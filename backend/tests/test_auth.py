import base64
import json
import time

import pytest
from fastapi.testclient import TestClient

from backend.app.auth import CognitoVerifier
from backend.app.config import Settings


def encoded(value: object) -> str:
    raw = base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":")).encode()).decode()
    return raw.rstrip("=")


def token(claims: dict[str, object]) -> tuple[str, dict[str, object]]:
    header = encoded({"alg": "RS256", "kid": "test"})
    body = encoded(claims)
    digest = __import__("hashlib").sha256(f"{header}.{body}".encode()).digest()
    expected = bytes.fromhex("3031300d060960864801650304020105000420") + digest
    size = 128
    signature = b"\x00\x01" + b"\xff" * (size - len(expected) - 3) + b"\x00" + expected
    value = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    jwk = {
        "keys": [
            {
                "kid": "test",
                "kty": "RSA",
                "n": base64.urlsafe_b64encode(b"\xff" * size).decode().rstrip("="),
                "e": base64.urlsafe_b64encode(b"\x01").decode().rstrip("="),
            }
        ]
    }
    return f"{header}.{body}.{value}", jwk


def test_cognito_verifier_checks_signature_claims_and_expiry() -> None:
    now = int(time.time())
    claims = {"iss": "https://issuer", "aud": "client", "token_use": "id", "exp": now + 60}
    value, jwks = token(claims)
    verifier = CognitoVerifier("https://issuer", "client", jwks)
    assert verifier.verify(value, now)["aud"] == "client"
    with pytest.raises(ValueError, match="Expired"):
        verifier.verify(value, now + 61)
    with pytest.raises(ValueError, match="audience"):
        CognitoVerifier("https://issuer", "other", jwks).verify(value, now)
    with pytest.raises(ValueError, match="signature"):
        verifier.verify(value[:-2] + "AA", now)


def test_cognito_identity_maps_to_database_role(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class StubVerifier:
        def verify(self, _token: str) -> dict[str, str]:
            return {"email": "customer@test.local", "cognito:groups": "admin"}

    settings = Settings(
        auth_mode="cognito",
        dev_auth_enabled=False,
        cognito_issuer="https://issuer",
        cognito_client_id="client",
        cognito_jwks_json='{"keys":[]}',
    )
    monkeypatch.setattr("backend.app.auth.get_settings", lambda: settings)
    monkeypatch.setattr("backend.app.auth._cognito_verifier", lambda: StubVerifier())
    response = client.get("/v1/me", headers={"Authorization": "Bearer token"})
    assert response.status_code == 200
    assert response.json()["role"] == "CUSTOMER"
