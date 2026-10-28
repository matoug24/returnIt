from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select, text

from backend.app.db import SessionLocal, engine
from backend.app.domain import DomainError, create_booking
from backend.app.models import Booking, Role, ServiceWindow, User
from backend.app.schemas import BookingCreate
from backend.tests.test_booking_api import booking_payload


@pytest.mark.postgres
def test_postgis_extension_available() -> None:
    if engine.dialect.name != "postgresql":
        pytest.skip("Set RETURNET_DATABASE_URL to the Compose PostgreSQL service to run this test")
    with engine.connect() as connection:
        version = connection.execute(text("SELECT PostGIS_Version()"))
        assert version.scalar_one()


@pytest.mark.postgres
def test_last_capacity_slot_is_serialized(ids: dict[str, str]) -> None:
    if engine.dialect.name != "postgresql":
        pytest.skip("Set RETURNET_DATABASE_URL to PostgreSQL to run the locking test")
    with SessionLocal() as db:
        window = db.get(ServiceWindow, ids["window"])
        assert window
        window.capacity = 1
        customer_ids = list(db.scalars(select(User.id).where(User.role == Role.CUSTOMER.value)))
        db.commit()

    def reserve(index: int) -> str:
        with SessionLocal() as db:
            try:
                create_booking(
                    db,
                    customer_ids[index],
                    "en-CA",
                    BookingCreate.model_validate(booking_payload(ids["window"], f"PG-{index}")),
                    f"postgres-capacity-{index}",
                    f"postgres-request-{index}",
                )
                return "created"
            except DomainError as exc:
                return str(exc.detail["code"])

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(reserve, range(2)))
    assert sorted(outcomes) == ["booking.window_full", "created"]
    with SessionLocal() as db:
        assert db.scalar(select(__import__("sqlalchemy").func.count(Booking.id))) == 1
