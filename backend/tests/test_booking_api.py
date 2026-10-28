from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import strategies as st
from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.domain import price, process_outbox_batch
from backend.app.models import BookingStatus, Notification, ServiceWindow
from backend.tests.conftest import auth


def booking_payload(window_id: str, label: str = "LABEL-001") -> dict[str, object]:
    destination_closes = datetime.now(UTC) + timedelta(days=2)
    return {
        "window_id": window_id,
        "pickup_address": {
            "line1": "1234 rue Sainte-Catherine O",
            "city": "Montréal",
            "province": "QC",
            "postal_code": "H3G 1P1",
            "latitude": 45.497,
            "longitude": -73.579,
        },
        "packages": [
            {
                "retailer": "Example",
                "carrier": "Canada Post",
                "label_code": label,
                "destination_name": "Post office",
                "destination_address": "1000 rue Example, Montréal",
                "destination_open_until": destination_closes.isoformat(),
                "weight_grams": 1000,
            }
        ],
        "payment_method": "fake_card",
        "accepted_terms_version": "pilot-v1",
        "package_attestation": True,
    }


def test_booking_is_idempotent_and_scoped(client: TestClient, ids: dict[str, str]) -> None:
    headers = auth("customer@test.local") | {"Idempotency-Key": "booking-key-001"}
    payload = booking_payload(ids["window"])
    first = client.post("/v1/bookings", json=payload, headers=headers)
    assert first.status_code == 201, first.text
    repeated = client.post("/v1/bookings", json=payload, headers=headers)
    assert repeated.status_code == 201
    assert repeated.json()["id"] == first.json()["id"]

    forbidden = client.get(f"/v1/bookings/{first.json()['id']}", headers=auth("other@test.local"))
    assert forbidden.status_code == 404

    changed = client.post(
        "/v1/bookings",
        json=booking_payload(ids["window"], "OTHER-LABEL"),
        headers=headers,
    )
    assert changed.status_code == 409
    assert changed.json()["error"]["code"] == "idempotency.key_reused"


def test_capacity_is_not_oversold(client: TestClient, ids: dict[str, str]) -> None:
    for index in range(2):
        result = client.post(
            "/v1/bookings",
            json=booking_payload(ids["window"], f"LABEL-{index}"),
            headers=auth("customer@test.local") | {"Idempotency-Key": f"capacity-key-{index}"},
        )
        assert result.status_code == 201
    result = client.post(
        "/v1/bookings",
        json=booking_payload(ids["window"], "LABEL-FULL"),
        headers=auth("other@test.local") | {"Idempotency-Key": "capacity-key-full"},
    )
    assert result.status_code == 409
    assert result.json()["error"]["code"] == "booking.window_full"


@given(st.integers(min_value=1, max_value=5))
def test_price_is_exact_and_monotonic(package_count: int) -> None:
    subtotal, tax, total = price(package_count)
    assert total == subtotal + tax
    assert subtotal > 0 and tax >= 0
    if package_count > 1:
        assert subtotal > price(package_count - 1)[0]


def test_webhook_deduplicates_and_accepts_reordered_events(client: TestClient) -> None:
    payload = {"id": "evt_001", "type": "payment_intent.succeeded", "data": {"id": "pi_1"}}
    headers = {"X-Returnet-Signature": "fake-local-webhook"}
    first = client.post("/v1/webhooks/stripe", json=payload, headers=headers)
    second = client.post("/v1/webhooks/stripe", json=payload, headers=headers)
    older_distinct = client.post(
        "/v1/webhooks/stripe",
        json={"id": "evt_000", "type": "payment_intent.processing", "data": {"id": "pi_1"}},
        headers=headers,
    )
    assert first.json() == {"accepted": True, "duplicate": False}
    assert second.json() == {"accepted": True, "duplicate": True}
    assert older_distinct.json() == {"accepted": True, "duplicate": False}


def test_reschedule_validates_preference_and_cancel_releases_capacity(
    client: TestClient, ids: dict[str, str]
) -> None:
    with SessionLocal() as db:
        original = db.get(ServiceWindow, ids["window"])
        assert original
        target = ServiceWindow(
            starts_at=original.starts_at + timedelta(days=1),
            ends_at=original.ends_at + timedelta(days=1),
            capacity=2,
        )
        db.add(target)
        db.commit()
        target_id = target.id
        target_start = target.starts_at
        target_end = target.ends_at

    booking = client.post(
        "/v1/bookings",
        json=booking_payload(ids["window"]),
        headers=auth("customer@test.local") | {"Idempotency-Key": "reschedule-booking-001"},
    ).json()
    invalid = client.post(
        f"/v1/bookings/{booking['id']}:reschedule",
        json={
            "expected_version": booking["version"],
            "window_id": target_id,
            "preferred_at": (target_end + timedelta(minutes=1)).isoformat(),
            "reason": "Test invalid preference",
        },
        headers=auth("customer@test.local"),
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "booking.preferred_outside_window"

    moved = client.post(
        f"/v1/bookings/{booking['id']}:reschedule",
        json={
            "expected_version": booking["version"],
            "window_id": target_id,
            "preferred_at": (target_start + timedelta(minutes=30)).isoformat(),
            "reason": "Customer changed day",
        },
        headers=auth("customer@test.local"),
    )
    assert moved.status_code == 200, moved.text

    cancelled = client.post(
        f"/v1/bookings/{booking['id']}:cancel",
        json={"expected_version": moved.json()["version"], "reason": "Customer cancelled"},
        headers=auth("customer@test.local"),
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == BookingStatus.CANCELLED.value
    with SessionLocal() as db:
        assert db.get(ServiceWindow, ids["window"]).reserved == 0  # type: ignore[union-attr]
        assert db.get(ServiceWindow, target_id).reserved == 0  # type: ignore[union-attr]


def test_local_notifications_use_booking_locale(client: TestClient, ids: dict[str, str]) -> None:
    response = client.post(
        "/v1/bookings",
        json=booking_payload(ids["window"]),
        headers=auth("other@test.local") | {"Idempotency-Key": "french-booking-001"},
    )
    assert response.status_code == 201
    with SessionLocal() as db:
        assert process_outbox_batch(db) == 1
        notification = db.scalar(
            select(Notification).where(Notification.booking_id == response.json()["id"])
        )
        assert notification
        assert notification.locale == "fr-CA"
        assert notification.subject == "Ramassage confirmé"


def test_finance_adjustment_is_limited_and_idempotent(
    client: TestClient, ids: dict[str, str]
) -> None:
    booking = client.post(
        "/v1/bookings",
        json=booking_payload(ids["window"]),
        headers=auth("customer@test.local") | {"Idempotency-Key": "refund-booking-001"},
    ).json()
    headers = auth("admin@test.local") | {"Idempotency-Key": "refund-adjustment-001"}
    payload = {
        "expected_version": booking["version"],
        "kind": "refund",
        "amount_cents": booking["total_cents"],
        "reason": "Customer-approved test refund",
    }
    first = client.post(
        f"/v1/finance/bookings/{booking['id']}/adjustments", json=payload, headers=headers
    )
    repeated = client.post(
        f"/v1/finance/bookings/{booking['id']}/adjustments", json=payload, headers=headers
    )
    assert first.status_code == 200
    assert repeated.json()["id"] == first.json()["id"]
