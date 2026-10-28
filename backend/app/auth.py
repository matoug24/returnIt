import base64
import hashlib
import json
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Annotated, Any, cast
from urllib.request import urlopen

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import Role, User


@dataclass(frozen=True)
class Principal:
    id: str
    email: str
    role: Role
    locale: str


class CognitoVerifier:
    """Small RS256 Cognito verifier; database users remain the role authority."""

    def __init__(self, issuer: str, client_id: str, jwks: Mapping[str, Any]) -> None:
        self.issuer = issuer.rstrip("/")
        self.client_id = client_id
        self.keys = {key["kid"]: key for key in jwks.get("keys", [])}

    @staticmethod
    def _decode(value: str) -> bytes:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

    def verify(self, token: str, now: int | None = None) -> Mapping[str, Any]:
        try:
            encoded_header, encoded_claims, encoded_signature = token.split(".")
            header = json.loads(self._decode(encoded_header))
            claims = json.loads(self._decode(encoded_claims))
            key = self.keys[header["kid"]]
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            raise ValueError("Malformed JWT") from exc
        if header.get("alg") != "RS256" or key.get("kty") != "RSA":
            raise ValueError("Unsupported JWT algorithm")
        modulus = int.from_bytes(self._decode(key["n"]), "big")
        exponent = int.from_bytes(self._decode(key["e"]), "big")
        signature = self._decode(encoded_signature)
        size = (modulus.bit_length() + 7) // 8
        signature_value = int.from_bytes(signature, "big")
        if signature_value >= modulus:
            raise ValueError("Invalid JWT signature")
        decoded = pow(signature_value, exponent, modulus).to_bytes(size, "big")
        digest = hashlib.sha256(f"{encoded_header}.{encoded_claims}".encode()).digest()
        expected = bytes.fromhex("3031300d060960864801650304020105000420") + digest
        padding = size - len(expected) - 3
        if padding < 8 or decoded != b"\x00\x01" + b"\xff" * padding + b"\x00" + expected:
            raise ValueError("Invalid JWT signature")
        timestamp = int(time.time()) if now is None else now
        audience = (
            claims.get("client_id") if claims.get("token_use") == "access" else claims.get("aud")
        )
        if claims.get("iss") != self.issuer or audience != self.client_id:
            raise ValueError("Invalid JWT issuer or audience")
        if claims.get("token_use") not in {"access", "id"}:
            raise ValueError("Invalid token use")
        if not isinstance(claims.get("exp"), int) or claims["exp"] <= timestamp:
            raise ValueError("Expired JWT")
        return cast(Mapping[str, Any], claims)


def _cognito_verifier() -> CognitoVerifier:
    settings = get_settings()
    if settings.cognito_jwks_json:
        jwks = json.loads(settings.cognito_jwks_json)
    else:
        with urlopen(settings.cognito_jwks_url, timeout=5) as response:  # noqa: S310
            jwks = json.load(response)
    return CognitoVerifier(settings.cognito_issuer, settings.cognito_client_id, jwks)


def current_principal(
    x_returnet_dev_user: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Principal:
    settings = get_settings()
    identity = x_returnet_dev_user
    if settings.auth_mode == "cognito":
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bearer token required")
        try:
            claims = _cognito_verifier().verify(authorization.removeprefix("Bearer "))
            identity = claims.get("email")
        except (ValueError, OSError, json.JSONDecodeError):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid bearer token") from None
    elif settings.auth_mode != "dev" or not settings.dev_auth_enabled:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Authentication unavailable")
    if not isinstance(identity, str) or not identity:
        detail = (
            "Token email required"
            if settings.auth_mode == "cognito"
            else "Development identity required"
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail)
    user = db.scalar(select(User).where(User.email == identity, User.active.is_(True)))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown or inactive identity")
    return Principal(user.id, user.email, Role(user.role), user.locale)


def require_roles(*roles: Role) -> Callable[..., Principal]:
    def dependency(
        principal: Annotated[Principal, Depends(current_principal)],
    ) -> Principal:
        if principal.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Role is not permitted")
        return principal

    return dependency
