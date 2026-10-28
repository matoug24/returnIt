import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import (
    AuditEvent,
    Booking,
    BookingStatus,
    CustodyEvent,
    Evidence,
    IdempotencyRecord,
    Notification,
    OutboxEvent,
    Package,
    PackageStatus,
    Payment,
    Route,
    RouteStatus,
    ServiceWindow,
    Stop,
    now_utc,
)
from .schemas import BookingCreate, CustodyCommand, ExceptionCommand, RoutePlanRequest


class DomainError(HTTPException):
    def __init__(self, code: str, message: str, http_status: int = 409, **details: Any):
        super().__init__(http_status, {"code": code, "message": message, "details": details})


def comparable_time(value: datetime) -> datetime:
    """Normalize SQLite-naive and PostgreSQL-aware timestamps for domain comparisons."""
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def payload_hash(payload: Any) -> str:
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def add_outbox(
    db: Session,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    version: int,
    payload: dict[str, Any],
    correlation_id: str,
) -> None:
    db.add(
        OutboxEvent(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            aggregate_version=version,
            payload=payload,
            correlation_id=correlation_id,
        )
    )


def audit(
    db: Session,
    actor_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    request_id: str,
    reason: str | None = None,
    **details: Any,
) -> None:
    db.add(
        AuditEvent(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id,
            reason=reason,
            details=details,
        )
    )


def get_idempotent(
    db: Session, principal_id: str, operation: str, key: str, body_hash: str
) -> dict[str, Any] | None:
    record = db.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.principal_id == principal_id,
            IdempotencyRecord.operation == operation,
            IdempotencyRecord.key == key,
        )
    )
    if not record:
        return None
    if record.request_hash != body_hash:
        raise DomainError(
            "idempotency.key_reused",
            "This idempotency key was already used for a different request.",
        )
    return record.response_json


def save_idempotent(
    db: Session,
    principal_id: str,
    operation: str,
    key: str,
    body_hash: str,
    response: dict[str, Any],
) -> None:
    db.add(
        IdempotencyRecord(
            principal_id=principal_id,
            operation=operation,
            key=key,
            request_hash=body_hash,
            response_status=201,
            response_json=response,
        )
    )


def price(package_count: int) -> tuple[int, int, int]:
    settings = get_settings()
    subtotal = (
        settings.pickup_price_cents + max(0, package_count - 1) * settings.extra_package_price_cents
    )
    tax = (subtotal * settings.tax_rate_bps + 5000) // 10000
    return subtotal, tax, subtotal + tax


def create_booking(
    db: Session,
    customer_id: str,
    locale: str,
    data: BookingCreate,
    idempotency_key: str,
    request_id: str,
) -> Booking:
    body_hash = payload_hash(data)
    cached = get_idempotent(db, customer_id, "create_booking", idempotency_key, body_hash)
    if cached:
        booking = db.get(Booking, cached["booking_id"])
        if not booking:
            raise DomainError(
                "idempotency.result_missing", "Stored booking result is unavailable.", 500
            )
        return booking

    window_query = select(ServiceWindow).where(ServiceWindow.id == data.window_id)
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        window_query = window_query.with_for_update()
    window = db.scalar(window_query)
    if not window or not window.active:
        raise DomainError("booking.window_unavailable", "Pickup window is unavailable.", 422)
    preferred = data.preferred_at
    if preferred and not (
        comparable_time(window.starts_at)
        <= comparable_time(preferred)
        <= comparable_time(window.ends_at)
    ):
        raise DomainError(
            "booking.preferred_outside_window",
            "Preferred time must be inside the confirmed pickup window.",
            422,
        )
    if window.reserved >= window.capacity:
        raise DomainError("booking.window_full", "Pickup window is full.")
    if any(
        comparable_time(package.destination_open_until) < comparable_time(window.ends_at)
        for package in data.packages
    ):
        raise DomainError(
            "booking.destination_hours_invalid",
            "A return destination closes before the pickup window ends.",
            422,
        )

    subtotal, tax, total = price(len(data.packages))
    if data.payment_method == "subscription":
        # A finite local entitlement is modelled as a deterministic pilot allowance.
        prior = (
            db.scalar(select(func.count(Booking.id)).where(Booking.customer_id == customer_id)) or 0
        )
        if prior >= get_settings().subscription_entitlements:
            raise DomainError(
                "subscription.entitlement_exhausted", "No pickup entitlement remains.", 402
            )
        payment_status, charged = "entitlement_consumed", 0
    else:
        payment_status, charged = "paid", total

    window.reserved += 1
    window.version += 1
    booking = Booking(
        reference=f"RET-{secrets.token_hex(3).upper()}",
        customer_id=customer_id,
        window_id=window.id,
        pickup_address=data.pickup_address.model_dump(),
        preferred_at=preferred,
        locale=locale,
        subtotal_cents=subtotal,
        tax_cents=tax,
        total_cents=total,
        payment_status=payment_status,
    )
    for index, package in enumerate(data.packages, 1):
        booking.packages.append(Package(ordinal=index, **package.model_dump()))
    db.add(booking)
    db.flush()
    payment = Payment(
        booking_id=booking.id,
        provider="fake",
        provider_id=f"fake_{secrets.token_hex(8)}",
        amount_cents=charged,
        status="succeeded",
        idempotency_key=idempotency_key,
    )
    db.add(payment)
    add_outbox(
        db,
        "booking.confirmed.v1",
        "booking",
        booking.id,
        booking.version,
        {"booking_id": booking.id, "locale": locale},
        request_id,
    )
    audit(db, customer_id, "booking.create", "booking", booking.id, request_id)
    save_idempotent(
        db,
        customer_id,
        "create_booking",
        idempotency_key,
        body_hash,
        {"booking_id": booking.id},
    )
    db.commit()
    db.refresh(booking)
    return booking


def plan_route(db: Session, request: RoutePlanRequest, actor_id: str, request_id: str) -> Route:
    bookings = list(
        db.scalars(
            select(Booking)
            .join(ServiceWindow)
            .where(
                Booking.status.in_([BookingStatus.CONFIRMED.value, BookingStatus.SCHEDULED.value]),
                func.date(ServiceWindow.starts_at) == request.service_date,
                Booking.route_id.is_(None),
            )
        ).all()
    )
    if not bookings:
        raise DomainError("routing.no_eligible_bookings", "No eligible bookings were found.", 422)
    total_weight = sum(package.weight_grams for b in bookings for package in b.packages)
    if total_weight > request.capacity_grams:
        raise DomainError(
            "routing.capacity_exceeded",
            "Route capacity is insufficient.",
            422,
            required_grams=total_weight,
        )
    ordered = sorted(bookings, key=lambda b: b.preferred_at or b.window.starts_at)
    cursor = request.shift_start
    planned: list[tuple[Booking, datetime]] = []
    for booking in ordered:
        candidate_naive = max(comparable_time(cursor), comparable_time(booking.window.starts_at))
        candidate = candidate_naive.replace(tzinfo=UTC)
        if candidate_naive > comparable_time(booking.window.ends_at):
            raise DomainError(
                "routing.infeasible_window",
                "At least one hard pickup window is infeasible.",
                422,
                booking_id=booking.id,
            )
        cursor = candidate + timedelta(minutes=8)
        if comparable_time(cursor) > comparable_time(request.shift_end):
            raise DomainError("routing.shift_exceeded", "Plan exceeds the driver shift.", 422)
        planned.append((booking, candidate))
    canonical = [f"{b.id}:{at.isoformat()}" for b, at in planned]
    route = Route(
        public_id=f"ROUTE-{secrets.token_hex(3).upper()}",
        driver_id=request.driver_id,
        service_date=request.service_date,
        input_hash=payload_hash(canonical),
        plan={
            "provider": "local_deterministic",
            "hard_constraints_validated": True,
            "soft_objective": "preferred_time_then_stable_order",
            "total_weight_grams": total_weight,
            "break_minutes": request.break_minutes,
        },
    )
    for sequence, (booking, planned_at) in enumerate(planned, 1):
        route.stops.append(
            Stop(
                booking_id=booking.id,
                sequence=sequence,
                planned_at=planned_at,
            )
        )
    db.add(route)
    db.flush()
    audit(db, actor_id, "route.plan", "route", route.id, request_id)
    add_outbox(
        db,
        "route.proposed.v1",
        "route",
        route.id,
        route.version,
        {"route_id": route.id},
        request_id,
    )
    db.commit()
    db.refresh(route)
    return route


def publish_route(
    db: Session, route: Route, expected_version: int, actor_id: str, reason: str, request_id: str
) -> Route:
    if route.version != expected_version or route.status != RouteStatus.PROPOSED.value:
        raise DomainError("route.version_conflict", "Route changed or cannot be published.")
    for stop in route.stops:
        booking = stop.booking
        if booking.route_id and booking.route_id != route.id:
            raise DomainError("route.booking_already_assigned", "A booking was already assigned.")
        if not (
            comparable_time(booking.window.starts_at)
            <= comparable_time(stop.planned_at)
            <= comparable_time(booking.window.ends_at)
        ):
            raise DomainError("route.hard_window_violation", "Route violates a hard pickup window.")
        booking.route_id = route.id
        booking.status = BookingStatus.ROUTE_LOCKED.value
        booking.version += 1
    route.status = RouteStatus.PUBLISHED.value
    route.version += 1
    route.published_at = now_utc()
    audit(db, actor_id, "route.publish", "route", route.id, request_id, reason)
    add_outbox(
        db,
        "route.published.v1",
        "route",
        route.id,
        route.version,
        {"route_id": route.id, "driver_id": route.driver_id},
        request_id,
    )
    db.commit()
    db.refresh(route)
    return route


TRANSITIONS: dict[str, dict[str, str]] = {
    "accept_pickup": {PackageStatus.EXPECTED.value: PackageStatus.IN_CUSTODY.value},
    "record_handoff": {PackageStatus.IN_CUSTODY.value: PackageStatus.HANDED_OFF.value},
}


def custody_transition(
    db: Session,
    package: Package,
    action: str,
    command: CustodyCommand,
    actor_id: str,
    request_id: str,
) -> Package:
    existing = db.scalar(select(CustodyEvent).where(CustodyEvent.command_id == command.command_id))
    if existing:
        return db.get(Package, existing.package_id)  # type: ignore[return-value]
    if package.version != command.expected_version:
        raise DomainError(
            "package.version_conflict", "Package changed; synchronize before retrying."
        )
    target = TRANSITIONS.get(action, {}).get(package.status)
    if not target:
        raise DomainError("package.invalid_transition", f"Cannot {action} from {package.status}.")
    if not command.evidence_ids:
        raise DomainError(
            "package.evidence_required", "At least one evidence item is required.", 422
        )
    evidences = list(
        db.scalars(select(Evidence).where(Evidence.id.in_(command.evidence_ids))).all()
    )
    if len(evidences) != len(set(command.evidence_ids)) or any(
        e.package_id != package.id for e in evidences
    ):
        raise DomainError(
            "package.evidence_invalid", "Evidence is missing or belongs to another package.", 422
        )
    prior = package.status
    sequence = (
        db.scalar(select(func.count(CustodyEvent.id)).where(CustodyEvent.package_id == package.id))
        or 0
    ) + 1
    event = CustodyEvent(
        package_id=package.id,
        sequence=sequence,
        event_type=action,
        from_status=prior,
        to_status=target,
        actor_id=actor_id,
        occurred_at=command.occurred_at,
        command_id=command.command_id,
        reason=command.reason,
        latitude=command.latitude,
        longitude=command.longitude,
        metadata_json={"tracking_reference": command.tracking_reference},
    )
    db.add(event)
    db.flush()
    for evidence in evidences:
        evidence.custody_event_id = event.id
    package.status = target
    package.version += 1
    booking = package.booking
    package_states = [p.status for p in booking.packages]
    if all(value == PackageStatus.HANDED_OFF.value for value in package_states):
        booking.status = BookingStatus.COMPLETED.value
    elif action == "accept_pickup":
        booking.status = BookingStatus.IN_PROGRESS.value
    else:
        booking.status = BookingStatus.PARTIALLY_COMPLETED.value
    booking.version += 1
    add_outbox(
        db,
        f"package.{action}.v1",
        "package",
        package.id,
        package.version,
        {"package_id": package.id, "booking_id": booking.id},
        request_id,
    )
    audit(db, actor_id, f"package.{action}", "package", package.id, request_id)
    db.commit()
    db.refresh(package)
    return package


def record_exception(
    db: Session,
    package: Package,
    command: ExceptionCommand,
    actor_id: str,
    request_id: str,
) -> Package:
    existing = db.scalar(select(CustodyEvent).where(CustodyEvent.command_id == command.command_id))
    if existing:
        return db.get(Package, existing.package_id)  # type: ignore[return-value]
    if package.version != command.expected_version:
        raise DomainError(
            "package.version_conflict", "Package changed; synchronize before retrying."
        )
    no_custody = {"customer_no_show", "invalid_label", "rejected_package"}
    target = (
        PackageStatus.NOT_COLLECTED.value
        if command.reason in no_custody
        else PackageStatus.IN_CUSTODY_EXCEPTION.value
    )
    if (
        target == PackageStatus.IN_CUSTODY_EXCEPTION.value
        and package.status != PackageStatus.IN_CUSTODY.value
    ):
        raise DomainError("package.invalid_transition", "This exception requires package custody.")
    prior = package.status
    event = CustodyEvent(
        package_id=package.id,
        sequence=(
            db.scalar(
                select(func.count(CustodyEvent.id)).where(CustodyEvent.package_id == package.id)
            )
            or 0
        )
        + 1,
        event_type="exception",
        from_status=prior,
        to_status=target,
        actor_id=actor_id,
        occurred_at=command.occurred_at,
        command_id=command.command_id,
        reason=command.reason,
        metadata_json={"evidence_ids": command.evidence_ids},
    )
    db.add(event)
    package.status = target
    package.version += 1
    package.booking.status = BookingStatus.EXCEPTION.value
    package.booking.version += 1
    add_outbox(
        db,
        "package.exception_opened.v1",
        "package",
        package.id,
        package.version,
        {"package_id": package.id, "booking_id": package.booking_id, "reason": command.reason},
        request_id,
    )
    audit(db, actor_id, "package.exception", "package", package.id, request_id, command.reason)
    db.commit()
    db.refresh(package)
    return package


MESSAGES = {
    "en-CA": {
        "booking.confirmed.v1": ("Pickup confirmed", "Your pickup window is confirmed."),
        "route.published.v1": (
            "Your pickup route has started",
            "Your driver is working the route. Your confirmed window still applies.",
        ),
        "booking.reminder.v1": (
            "Pickup reminder",
            "Please seal and label your return before your confirmed window.",
        ),
        "eta.approximately_15_minutes.v1": (
            "Driver about 15 minutes away",
            "This is an estimate. Your confirmed pickup window still applies.",
        ),
        "eta.approximately_1_minute.v1": (
            "Driver about 1 minute away",
            "Please have your prepared package ready. This arrival time is estimated.",
        ),
        "route.delayed.v1": (
            "Pickup delay",
            "Your driver is delayed. See the app for the latest estimate and options.",
        ),
        "package.accept_pickup.v1": (
            "Package picked up",
            "Your package is now in Returnet's custody.",
        ),
        "package.record_handoff.v1": (
            "Return delivered",
            "Your package was handed to the authorized return destination.",
        ),
        "package.exception_opened.v1": (
            "Pickup update",
            "There is an issue with your return. See the app for next steps.",
        ),
    },
    "fr-CA": {
        "booking.confirmed.v1": ("Ramassage confirmé", "Votre plage de ramassage est confirmée."),
        "route.published.v1": (
            "Votre tournée de ramassage a commencé",
            "Le chauffeur effectue la tournée. Votre plage confirmée s'applique toujours.",
        ),
        "booking.reminder.v1": (
            "Rappel de ramassage",
            "Veuillez fermer et étiqueter votre retour avant votre plage confirmée.",
        ),
        "eta.approximately_15_minutes.v1": (
            "Chauffeur à environ 15 minutes",
            "Il s'agit d'une estimation. Votre plage de ramassage confirmée s'applique toujours.",
        ),
        "eta.approximately_1_minute.v1": (
            "Chauffeur à environ 1 minute",
            "Veuillez préparer votre colis. L'heure d'arrivée demeure une estimation.",
        ),
        "route.delayed.v1": (
            "Retard du ramassage",
            "Votre chauffeur est retardé. Consultez l'application pour "
            "l'estimation et les options.",
        ),
        "package.accept_pickup.v1": (
            "Colis ramassé",
            "Votre colis est maintenant sous la garde de Returnet.",
        ),
        "package.record_handoff.v1": (
            "Retour livré",
            "Votre colis a été remis au point de retour autorisé.",
        ),
        "package.exception_opened.v1": (
            "Mise à jour du ramassage",
            "Un problème touche votre retour. Consultez l'application pour la suite.",
        ),
    },
}


def process_outbox_batch(db: Session, limit: int = 50) -> int:
    events = list(
        db.scalars(
            select(OutboxEvent)
            .where(OutboxEvent.published_at.is_(None))
            .order_by(OutboxEvent.created_at)
            .limit(limit)
        ).all()
    )
    for event in events:
        try:
            booking_id = event.payload.get("booking_id")
            if not booking_id and event.aggregate_type == "booking":
                booking_id = event.aggregate_id
            if event.event_type == "route.published.v1":
                route = db.get(Route, event.aggregate_id)
                booking_ids = [stop.booking_id for stop in route.stops] if route else []
            else:
                booking_ids = [booking_id] if booking_id else []
            for item_id in booking_ids:
                booking = db.get(Booking, item_id)
                if not booking:
                    continue
                localized = MESSAGES.get(booking.locale, MESSAGES["en-CA"])
                subject, body = localized.get(
                    event.event_type, ("Returnet update", "Your return status changed.")
                )
                dedupe = f"{booking.id}:{event.event_type}:{event.aggregate_version}"
                exists = db.scalar(select(Notification).where(Notification.dedupe_key == dedupe))
                if not exists:
                    db.add(
                        Notification(
                            booking_id=booking.id,
                            event_type=event.event_type,
                            channel="local",
                            locale=booking.locale,
                            dedupe_key=dedupe,
                            status="sent",
                            subject=subject,
                            body=body,
                            attempts=1,
                            sent_at=now_utc(),
                        )
                    )
            event.published_at = now_utc()
            event.attempts += 1
        except Exception as exc:  # worker must preserve event for retry
            event.attempts += 1
            event.last_error = str(exc)[:500]
    db.commit()
    return len(events)
