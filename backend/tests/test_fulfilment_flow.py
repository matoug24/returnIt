from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.app.db import SessionLocal
from backend.app.domain import process_outbox_batch
from backend.app.models import CustodyEvent, Notification, PackageStatus, Stop
from backend.tests.conftest import auth
from backend.tests.test_booking_api import booking_payload


def test_customer_to_dispatch_to_driver_handoff(client: TestClient, ids: dict[str, str]) -> None:
    booking_response = client.post(
        "/v1/bookings",
        json=booking_payload(ids["window"]),
        headers=auth("customer@test.local") | {"Idempotency-Key": "flow-booking-001"},
    )
    assert booking_response.status_code == 201, booking_response.text
    booking = booking_response.json()
    package = booking["packages"][0]

    window_start = datetime.fromisoformat(ids["window_start"]).replace(tzinfo=UTC)
    window_end = datetime.fromisoformat(ids["window_end"]).replace(tzinfo=UTC)
    shift_start = window_start - timedelta(hours=1)
    route_response = client.post(
        "/v1/ops/route-plans",
        json={
            "service_date": (datetime.now(UTC) + timedelta(days=1)).date().isoformat(),
            "driver_id": ids["driver"],
            "shift_start": shift_start.isoformat(),
            "shift_end": (window_end + timedelta(hours=4)).isoformat(),
            "capacity_grams": 100_000,
        },
        headers=auth("dispatch@test.local"),
    )
    assert route_response.status_code == 201, route_response.text
    route = route_response.json()
    publish = client.post(
        f"/v1/ops/routes/{route['id']}:publish",
        json={"expected_version": route["version"], "reason": "Reviewed for test"},
        headers=auth("dispatch@test.local"),
    )
    assert publish.status_code == 200, publish.text
    work = client.get("/v1/driver/routes/current/work", headers=auth("driver@test.local"))
    assert work.status_code == 200
    assert work.json()["stops"][0]["packages"][0]["id"] == package["id"]

    evidence = client.post(
        "/v1/evidence/uploads",
        json={
            "package_id": package["id"],
            "kind": "scan",
            "checksum": "checksum-pickup-001",
            "captured_at": datetime.now(UTC).isoformat(),
            "content_type": "text/plain",
        },
        headers=auth("driver@test.local"),
    )
    assert evidence.status_code == 201, evidence.text
    upload = client.put(
        f"/v1/evidence/{evidence.json()['id']}/content",
        files={"file": ("scan.txt", b"safe demo scan", "text/plain")},
        headers=auth("driver@test.local"),
    )
    assert upload.status_code == 200

    pickup = client.post(
        f"/v1/driver/packages/{package['id']}:accept_pickup",
        json={
            "command_id": "offline-command-pickup-001",
            "expected_version": package["version"],
            "occurred_at": datetime.now(UTC).isoformat(),
            "evidence_ids": [evidence.json()["id"]],
            "latitude": 45.497,
            "longitude": -73.579,
        },
        headers=auth("driver@test.local"),
    )
    assert pickup.status_code == 200, pickup.text
    assert pickup.json()["status"] == PackageStatus.IN_CUSTODY.value
    duplicate = client.post(
        f"/v1/driver/packages/{package['id']}:accept_pickup",
        json={
            "command_id": "offline-command-pickup-001",
            "expected_version": package["version"],
            "occurred_at": datetime.now(UTC).isoformat(),
            "evidence_ids": [evidence.json()["id"]],
        },
        headers=auth("driver@test.local"),
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["version"] == pickup.json()["version"]

    handoff_evidence = client.post(
        "/v1/evidence/uploads",
        json={
            "package_id": package["id"],
            "kind": "receipt",
            "checksum": "checksum-handoff-001",
            "captured_at": datetime.now(UTC).isoformat(),
        },
        headers=auth("driver@test.local"),
    ).json()
    handoff = client.post(
        f"/v1/driver/packages/{package['id']}:record_handoff",
        json={
            "command_id": "offline-command-handoff-001",
            "expected_version": pickup.json()["version"],
            "occurred_at": datetime.now(UTC).isoformat(),
            "evidence_ids": [handoff_evidence["id"]],
            "tracking_reference": "DEMO-TRACK-001",
        },
        headers=auth("driver@test.local"),
    )
    assert handoff.status_code == 200, handoff.text
    assert handoff.json()["status"] == PackageStatus.HANDED_OFF.value
    customer_proof = client.get(
        f"/v1/bookings/{booking['id']}/evidence", headers=auth("customer@test.local")
    )
    assert customer_proof.status_code == 200
    assert {item["kind"] for item in customer_proof.json()} == {"scan", "receipt"}
    forbidden_ops_proof = client.get(
        f"/v1/ops/packages/{package['id']}/evidence", headers=auth("customer@test.local")
    )
    assert forbidden_ops_proof.status_code == 403

    with SessionLocal() as db:
        assert db.scalar(select(func.count(CustodyEvent.id))) == 2
        processed = process_outbox_batch(db)
        assert processed >= 4
        notification_count = db.scalar(select(func.count(Notification.id)))
        assert notification_count >= 4
        assert process_outbox_batch(db) == 0
        assert db.scalar(select(func.count(Notification.id))) == notification_count


def test_exception_replay_is_idempotent_and_stale_commands_conflict(
    client: TestClient, ids: dict[str, str]
) -> None:
    booking = client.post(
        "/v1/bookings",
        json=booking_payload(ids["window"]),
        headers=auth("customer@test.local") | {"Idempotency-Key": "exception-booking-001"},
    ).json()
    package = booking["packages"][0]
    window_start = datetime.fromisoformat(ids["window_start"]).replace(tzinfo=UTC)
    window_end = datetime.fromisoformat(ids["window_end"]).replace(tzinfo=UTC)
    route = client.post(
        "/v1/ops/route-plans",
        json={
            "service_date": (datetime.now(UTC) + timedelta(days=1)).date().isoformat(),
            "driver_id": ids["driver"],
            "shift_start": (window_start - timedelta(hours=1)).isoformat(),
            "shift_end": (window_end + timedelta(hours=1)).isoformat(),
            "capacity_grams": 100_000,
        },
        headers=auth("dispatch@test.local"),
    ).json()
    publish = client.post(
        f"/v1/ops/routes/{route['id']}:publish",
        json={"expected_version": route["version"], "reason": "Reviewed for exception test"},
        headers=auth("dispatch@test.local"),
    )
    assert publish.status_code == 200

    command = {
        "command_id": "exception-command-001",
        "expected_version": package["version"],
        "occurred_at": datetime.now(UTC).isoformat(),
        "reason": "customer_no_show",
    }
    first = client.post(
        f"/v1/driver/packages/{package['id']}:exception",
        json=command,
        headers=auth("driver@test.local"),
    )
    assert first.status_code == 200, first.text
    assert first.json()["status"] == PackageStatus.NOT_COLLECTED.value

    replay = client.post(
        f"/v1/driver/packages/{package['id']}:exception",
        json=command,
        headers=auth("driver@test.local"),
    )
    assert replay.status_code == 200
    assert replay.json()["version"] == first.json()["version"]

    stale = client.post(
        f"/v1/driver/packages/{package['id']}:exception",
        json=command | {"command_id": "exception-command-002"},
        headers=auth("driver@test.local"),
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "package.version_conflict"

    with SessionLocal() as db:
        assert db.scalar(select(func.count(CustodyEvent.id))) == 1


def test_route_publish_revalidates_hard_windows(client: TestClient, ids: dict[str, str]) -> None:
    client.post(
        "/v1/bookings",
        json=booking_payload(ids["window"]),
        headers=auth("customer@test.local") | {"Idempotency-Key": "window-booking-001"},
    )
    window_start = datetime.fromisoformat(ids["window_start"]).replace(tzinfo=UTC)
    window_end = datetime.fromisoformat(ids["window_end"]).replace(tzinfo=UTC)
    route = client.post(
        "/v1/ops/route-plans",
        json={
            "service_date": (datetime.now(UTC) + timedelta(days=1)).date().isoformat(),
            "driver_id": ids["driver"],
            "shift_start": (window_start - timedelta(hours=1)).isoformat(),
            "shift_end": (window_end + timedelta(hours=1)).isoformat(),
            "capacity_grams": 100_000,
        },
        headers=auth("dispatch@test.local"),
    ).json()
    with SessionLocal() as db:
        stop = db.scalar(select(Stop).where(Stop.route_id == route["id"]))
        assert stop
        stop.planned_at = window_end + timedelta(minutes=1)
        db.commit()

    publish = client.post(
        f"/v1/ops/routes/{route['id']}:publish",
        json={"expected_version": route["version"], "reason": "Must be rejected"},
        headers=auth("dispatch@test.local"),
    )
    assert publish.status_code == 409
    assert publish.json()["error"]["code"] == "route.hard_window_violation"


def test_driver_cannot_read_customer_booking(client: TestClient, ids: dict[str, str]) -> None:
    booking = client.post(
        "/v1/bookings",
        json=booking_payload(ids["window"]),
        headers=auth("customer@test.local") | {"Idempotency-Key": "scope-booking-001"},
    ).json()
    response = client.get(f"/v1/bookings/{booking['id']}", headers=auth("driver@test.local"))
    assert response.status_code == 404
