from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from .db import Base, SessionLocal, engine
from .domain import create_booking, plan_route, process_outbox_batch, publish_route
from .models import Role, ServiceWindow, User
from .schemas import AddressInput, BookingCreate, PackageInput, RoutePlanRequest

USERS = [
    ("customer@local.returnet.ca", "Camille Tremblay", Role.CUSTOMER, "fr-CA"),
    ("customer-en@local.returnet.ca", "Alex Morgan", Role.CUSTOMER, "en-CA"),
    ("driver@local.returnet.ca", "Samira Driver", Role.DRIVER, "fr-CA"),
    ("dispatch@local.returnet.ca", "Dispatch Demo", Role.DISPATCHER, "en-CA"),
    ("admin@local.returnet.ca", "Admin Demo", Role.ADMIN, "en-CA"),
    ("support@local.returnet.ca", "Support Demo", Role.SUPPORT, "fr-CA"),
    ("finance@local.returnet.ca", "Finance Demo", Role.FINANCE, "en-CA"),
]


def seed() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.scalar(select(User).limit(1)):
            print("Seed data already exists; no changes made.")
            return
        for email, name, role, locale in USERS:
            db.add(User(email=email, name=name, role=role.value, locale=locale))
        tomorrow = (datetime.now(UTC) + timedelta(days=1)).replace(
            hour=14, minute=0, second=0, microsecond=0
        )
        window = ServiceWindow(
            starts_at=tomorrow, ends_at=tomorrow + timedelta(hours=4), capacity=12
        )
        db.add(window)
        db.commit()
        customer = db.scalar(select(User).where(User.email == "customer@local.returnet.ca"))
        assert customer
        booking = create_booking(
            db,
            customer.id,
            customer.locale,
            BookingCreate(
                window_id=window.id,
                pickup_address=AddressInput(
                    line1="1250 boulevard René-Lévesque O",
                    postal_code="H3B 4W8",
                    latitude=45.4972,
                    longitude=-73.5713,
                ),
                preferred_at=tomorrow + timedelta(hours=1),
                packages=[
                    PackageInput(
                        retailer="Demo Boutique",
                        carrier="Canada Post",
                        label_code="DEMO-LABEL-001",
                        destination_name="Canada Post — Downtown",
                        destination_address="1000 Rue Sainte-Catherine O, Montréal, QC",
                        destination_open_until=tomorrow + timedelta(hours=8),
                        weight_grams=1200,
                    )
                ],
                payment_method="fake_card",
                accepted_terms_version="pilot-v1",
                package_attestation=True,
            ),
            "seed-booking-001",
            "seed-request",
        )
        driver = db.scalar(select(User).where(User.role == Role.DRIVER.value))
        dispatcher = db.scalar(select(User).where(User.role == Role.DISPATCHER.value))
        assert driver and dispatcher
        route = plan_route(
            db,
            RoutePlanRequest(
                service_date=tomorrow.date().isoformat(),
                driver_id=driver.id,
                shift_start=tomorrow - timedelta(hours=1),
                shift_end=tomorrow + timedelta(hours=8),
                capacity_grams=100_000,
            ),
            dispatcher.id,
            "seed-route",
        )
        publish_route(db, route, route.version, dispatcher.id, "Demo route", "seed-publish")
        process_outbox_batch(db)
        print("Seed complete.")
        print(f"Demo booking: {booking.reference}")
        print("Use X-Returnet-Dev-User with an @local.returnet.ca account from README.md")


if __name__ == "__main__":
    seed()
