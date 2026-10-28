from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="RETURNET_", extra="ignore")

    env: str = "development"
    database_url: str = "sqlite:///./returnet.db"
    database_host: str = ""
    database_port: int = 5432
    database_name: str = "returnet"
    database_user: str = ""
    database_password: str = ""
    auth_mode: str = "dev"
    dev_auth_enabled: bool = True
    cognito_issuer: str = ""
    cognito_client_id: str = ""
    cognito_jwks_url: str = ""
    cognito_jwks_json: str = ""
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:8081"]
    upload_dir: Path = Path("uploads")
    queue_mode: str = "local"
    sqs_queue_url: str = ""
    sqs_wait_seconds: int = 20
    payment_provider: str = "fake"
    routing_provider: str = "local"
    notification_provider: str = "local"
    pickup_price_cents: int = 1499
    extra_package_price_cents: int = 399
    subscription_monthly_cents: int = 2999
    subscription_entitlements: int = 3
    tax_rate_bps: int = 1498
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    google_route_optimization_project_id: str = ""

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        return value.split(",") if isinstance(value, str) else value

    @model_validator(mode="after")
    def protect_production(self) -> "Settings":
        if self.database_host:
            self.database_url = (
                "postgresql+psycopg://"
                f"{quote_plus(self.database_user)}:{quote_plus(self.database_password)}"
                f"@{self.database_host}:{self.database_port}/{self.database_name}"
            )
        if self.env in {"production", "staging"} and (
            self.dev_auth_enabled or self.auth_mode == "dev"
        ):
            raise ValueError("Development authentication is forbidden outside development/test")
        if self.auth_mode == "cognito" and not (
            self.cognito_issuer
            and self.cognito_client_id
            and (self.cognito_jwks_url or self.cognito_jwks_json)
        ):
            raise ValueError("Cognito mode requires issuer, client id, and JWKS configuration")
        if self.queue_mode == "sqs" and not self.sqs_queue_url:
            raise ValueError("SQS mode requires a queue URL")
        if self.payment_provider == "stripe" and not self.stripe_secret_key:
            raise ValueError("Stripe mode requires a secret key")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
