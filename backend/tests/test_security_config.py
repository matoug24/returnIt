import pytest
from pydantic import ValidationError

from backend.app.config import Settings


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_dev_auth_cannot_start_outside_development_or_test(environment: str) -> None:
    with pytest.raises(ValidationError):
        Settings(env=environment, auth_mode="dev", dev_auth_enabled=True)


def test_stripe_mode_requires_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(payment_provider="stripe", stripe_secret_key="")


def test_cognito_and_sqs_modes_require_complete_configuration() -> None:
    with pytest.raises(ValidationError):
        Settings(auth_mode="cognito", dev_auth_enabled=False)
    with pytest.raises(ValidationError):
        Settings(queue_mode="sqs")
