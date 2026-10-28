from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.db import Base, SessionLocal, engine
from backend.app.main import app
from backend.app.models import Role, ServiceWindow, User


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        users = [
            User(
                email="customer@test.local",
                name="Customer",
                role=Role.CUSTOMER.value,
                locale="en-CA",
            ),
            User(email="other@test.local", name="Other", role=Role.CUSTOMER.value, locale="fr-CA"),
            User(email="driver@test.local", name="Driver", role=Role.DRIVER.value, locale="fr-CA"),
            User(email="dispatch@test.local", name="Dispatch", role=Role.DISPATCHER.value),
            User(email="admin@test.local", name="Admin", role=Role.ADMIN.value),
        ]
        starts = (datetime.now(UTC) + timedelta(days=1)).replace(
            hour=14, minute=0, second=0, microsecond=0
        )
        db.add_all(users)
        db.add(ServiceWindow(starts_at=starts, ends_at=starts + timedelta(hours=4), capacity=2))
        db.commit()
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def ids() -> dict[str, str]:
    with SessionLocal() as db:
        window = db.scalar(select(ServiceWindow))
        assert window
        return {
            "window": window.id,
            "window_start": window.starts_at.isoformat(),
            "window_end": window.ends_at.isoformat(),
            "driver": db.scalar(select(User.id).where(User.role == Role.DRIVER.value)),
        }


def auth(email: str) -> dict[str, str]:
    return {"X-Returnet-Dev-User": email}
