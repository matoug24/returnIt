import secrets
from datetime import datetime
from pathlib import Path
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .auth import Principal, current_principal, require_roles
from .config import get_settings
from .db import get_db
from .domain import (
    DomainError,
    add_outbox,
    audit,
    comparable_time,
    create_booking,
    custody_transition,
    plan_route,
    price,
    publish_route,
    record_exception,
)
from .models import (
    AuditEvent,
    Booking,
    BookingStatus,
    Evidence,
    Package,
    Payment,
    Role,
    Route,
    RouteStatus,
    ServiceWindow,
    Stop,
    User,
    WebhookInbox,
    now_utc,
)
from .schemas import (
    BookingAction,
    BookingCreate,
    BookingView,
    CustodyCommand,
    EvidenceCreate,
    EvidenceView,
    ExceptionCommand,
    FinancialAdjustment,
    PackageView,
    PublishRoute,
    RescheduleAction,
    RoutePlanRequest,
    RouteView,
    WebhookEvent,
    WindowView,
)

router = APIRouter(prefix="/v1")
DB = Annotated[Session, Depends(get_db)]
Current = Annotated[Principal, Depends(current_principal)]


def request_id(request: Request) -> str:
    return cast(str, request.state.request_id)


def load_booking(db: Session, booking_id: str) -> Booking:
    booking = db.scalar(
        select(Booking)
        .options(selectinload(Booking.packages), selectinload(Booking.window))
        .where(Booking.id == booking_id)
    )
    if not booking:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    return booking


def authorize_booking(principal: Principal, booking: Booking) -> None:
    staff = {Role.ADMIN, Role.DISPATCHER, Role.SUPPORT, Role.FINANCE}
    if principal.role not in staff and booking.customer_id != principal.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")


def authorize_driver_package(db: Session, principal: Principal, package: Package) -> None:
    if principal.role in {Role.ADMIN, Role.DISPATCHER}:
        return
    booking = package.booking
    route = db.get(Route, booking.route_id) if booking.route_id else None
    if principal.role != Role.DRIVER or not route or route.driver_id != principal.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Package not found")


@router.get("/me")
def me(principal: Current) -> dict[str, str]:
    return {
        "id": principal.id,
        "email": principal.email,
        "role": principal.role.value,
        "locale": principal.locale,
    }


@router.get("/availability", response_model=list[WindowView])
def availability(
    db: DB,
    _principal: Current,
    date_from: datetime | None = Query(default=None),
) -> list[ServiceWindow]:
    query = select(ServiceWindow).where(
        ServiceWindow.active.is_(True), ServiceWindow.reserved < ServiceWindow.capacity
    )
    if date_from:
        query = query.where(ServiceWindow.ends_at >= date_from)
    return list(db.scalars(query.order_by(ServiceWindow.starts_at).limit(30)).all())


@router.get("/serviceability")
def serviceability(postal_code: str, _principal: Current) -> dict[str, object]:
    normalized = postal_code.upper().replace(" ", "")
    eligible = normalized.startswith(("H1", "H2", "H3", "H4")) and len(normalized) == 6
    return {"eligible": eligible, "zone": "Montreal Core" if eligible else None}


@router.get("/pricing/quote")
def pricing_quote(
    _principal: Current,
    package_count: int = Query(default=1, ge=1, le=5),
    payment_method: str = Query(default="fake_card", pattern="^(fake_card|subscription)$"),
) -> dict[str, int | str]:
    subtotal, tax, total = price(package_count)
    return {
        "payment_method": payment_method,
        "subtotal_cents": subtotal,
        "tax_cents": tax,
        "total_cents": 0 if payment_method == "subscription" else total,
    }


@router.post("/bookings", response_model=BookingView, status_code=201)
def post_booking(
    data: BookingCreate,
    request: Request,
    db: DB,
    principal: Annotated[Principal, Depends(require_roles(Role.CUSTOMER))],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=120)],
) -> Booking:
    return create_booking(
        db, principal.id, principal.locale, data, idempotency_key, request_id(request)
    )


@router.get("/bookings", response_model=list[BookingView])
def list_bookings(
    db: DB, principal: Current, limit: int = Query(default=20, ge=1, le=100)
) -> list[Booking]:
    query = (
        select(Booking).options(selectinload(Booking.packages)).order_by(Booking.created_at.desc())
    )
    if principal.role == Role.CUSTOMER:
        query = query.where(Booking.customer_id == principal.id)
    elif principal.role not in {Role.ADMIN, Role.DISPATCHER, Role.SUPPORT, Role.FINANCE}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Role is not permitted")
    return list(db.scalars(query.limit(limit)).unique().all())


@router.get("/bookings/{booking_id}", response_model=BookingView)
def get_booking(booking_id: str, db: DB, principal: Current) -> Booking:
    booking = load_booking(db, booking_id)
    authorize_booking(principal, booking)
    return booking


@router.get("/bookings/{booking_id}/evidence", response_model=list[EvidenceView])
def booking_evidence(booking_id: str, db: DB, principal: Current) -> list[Evidence]:
    booking = load_booking(db, booking_id)
    authorize_booking(principal, booking)
    package_ids = [package.id for package in booking.packages]
    return list(db.scalars(select(Evidence).where(Evidence.package_id.in_(package_ids))).all())


@router.post("/bookings/{booking_id}:cancel", response_model=BookingView)
def cancel_booking(
    booking_id: str, data: BookingAction, request: Request, db: DB, principal: Current
) -> Booking:
    booking = load_booking(db, booking_id)
    authorize_booking(principal, booking)
    if booking.version != data.expected_version:
        raise DomainError("booking.version_conflict", "Booking changed; refresh before retrying.")
    if booking.status not in {
        BookingStatus.CONFIRMED.value,
        BookingStatus.SCHEDULED.value,
        BookingStatus.ROUTE_LOCKED.value,
    }:
        raise DomainError("booking.cannot_cancel", "Booking can no longer be cancelled.")
    booking.window.reserved = max(0, booking.window.reserved - 1)
    booking.window.version += 1
    booking.status = BookingStatus.CANCELLED.value
    booking.version += 1
    add_outbox(
        db,
        "booking.cancelled.v1",
        "booking",
        booking.id,
        booking.version,
        {"booking_id": booking.id},
        request_id(request),
    )
    audit(
        db, principal.id, "booking.cancel", "booking", booking.id, request_id(request), data.reason
    )
    db.commit()
    return booking


@router.post("/bookings/{booking_id}:reschedule", response_model=BookingView)
def reschedule_booking(
    booking_id: str, data: RescheduleAction, request: Request, db: DB, principal: Current
) -> Booking:
    booking = load_booking(db, booking_id)
    authorize_booking(principal, booking)
    if booking.version != data.expected_version:
        raise DomainError("booking.version_conflict", "Booking changed; refresh before retrying.")
    if booking.status not in {BookingStatus.CONFIRMED.value, BookingStatus.SCHEDULED.value}:
        raise DomainError("booking.cannot_reschedule", "Booking can no longer be rescheduled.")
    target = db.get(ServiceWindow, data.window_id)
    if not target or not target.active or target.reserved >= target.capacity:
        raise DomainError("booking.window_unavailable", "Pickup window is unavailable.")
    if data.preferred_at and not (
        comparable_time(target.starts_at)
        <= comparable_time(data.preferred_at)
        <= comparable_time(target.ends_at)
    ):
        raise DomainError(
            "booking.preferred_outside_window",
            "Preferred time must be inside the pickup window.",
            422,
        )
    booking.window.reserved = max(0, booking.window.reserved - 1)
    booking.window.version += 1
    target.reserved += 1
    target.version += 1
    booking.window_id = target.id
    booking.preferred_at = data.preferred_at
    booking.version += 1
    add_outbox(
        db,
        "booking.rescheduled.v1",
        "booking",
        booking.id,
        booking.version,
        {"booking_id": booking.id},
        request_id(request),
    )
    audit(
        db,
        principal.id,
        "booking.reschedule",
        "booking",
        booking.id,
        request_id(request),
        data.reason,
    )
    db.commit()
    db.refresh(booking)
    return booking


@router.post("/ops/route-plans", response_model=RouteView, status_code=201)
def create_route_plan(
    data: RoutePlanRequest,
    request: Request,
    db: DB,
    principal: Annotated[Principal, Depends(require_roles(Role.DISPATCHER, Role.ADMIN))],
) -> Route:
    driver = db.get(User, data.driver_id)
    if not driver or driver.role != Role.DRIVER.value:
        raise DomainError("routing.driver_invalid", "Driver is invalid.", 422)
    return plan_route(db, data, principal.id, request_id(request))


@router.get("/ops/routes", response_model=list[RouteView])
def list_routes(
    db: DB,
    _principal: Annotated[
        Principal, Depends(require_roles(Role.DISPATCHER, Role.ADMIN, Role.SUPPORT))
    ],
) -> list[Route]:
    return list(
        db.scalars(
            select(Route).options(selectinload(Route.stops)).order_by(Route.created_at.desc())
        )
        .unique()
        .all()
    )


@router.get("/ops/routes/{route_id}", response_model=RouteView)
def get_route(
    route_id: str,
    db: DB,
    _principal: Annotated[
        Principal, Depends(require_roles(Role.DISPATCHER, Role.ADMIN, Role.SUPPORT))
    ],
) -> Route:
    route = db.scalar(
        select(Route).options(selectinload(Route.stops)).where(Route.id == route_id)
    )
    if not route:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Route not found")
    return route


@router.get("/ops/drivers")
def list_drivers(
    db: DB,
    _principal: Annotated[Principal, Depends(require_roles(Role.DISPATCHER, Role.ADMIN))],
) -> list[dict[str, str]]:
    drivers = db.scalars(
        select(User)
        .where(User.role == Role.DRIVER.value, User.active.is_(True))
        .order_by(User.name)
    ).all()
    return [{"id": driver.id, "name": driver.name, "email": driver.email} for driver in drivers]


@router.get("/ops/packages/{package_id}/evidence", response_model=list[EvidenceView])
def list_package_evidence(
    package_id: str,
    db: DB,
    _principal: Annotated[
        Principal, Depends(require_roles(Role.DISPATCHER, Role.ADMIN, Role.SUPPORT, Role.FINANCE))
    ],
) -> list[Evidence]:
    if not db.get(Package, package_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Package not found")
    return list(db.scalars(select(Evidence).where(Evidence.package_id == package_id)).all())


@router.post("/ops/routes/{route_id}:publish", response_model=RouteView)
def post_publish_route(
    route_id: str,
    data: PublishRoute,
    request: Request,
    db: DB,
    principal: Annotated[Principal, Depends(require_roles(Role.DISPATCHER, Role.ADMIN))],
) -> Route:
    route_query = (
        select(Route)
        .options(selectinload(Route.stops).selectinload(Stop.booking).selectinload(Booking.window))
        .where(Route.id == route_id)
    )
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        route_query = route_query.with_for_update()
    route = db.scalar(route_query)
    if not route:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Route not found")
    return publish_route(
        db, route, data.expected_version, principal.id, data.reason, request_id(request)
    )


@router.get("/driver/routes/current", response_model=RouteView)
def driver_route(
    db: DB,
    principal: Annotated[Principal, Depends(require_roles(Role.DRIVER))],
) -> Route:
    route = db.scalar(
        select(Route)
        .options(selectinload(Route.stops))
        .where(
            Route.driver_id == principal.id,
            Route.status.in_([RouteStatus.PUBLISHED.value, RouteStatus.ACTIVE.value]),
        )
        .order_by(Route.created_at.desc())
    )
    if not route:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No active route")
    return route


@router.get("/driver/routes/current/work")
def driver_work(
    db: DB,
    principal: Annotated[Principal, Depends(require_roles(Role.DRIVER))],
) -> dict[str, object]:
    route = db.scalar(
        select(Route)
        .options(
            selectinload(Route.stops).selectinload(Stop.booking).selectinload(Booking.packages)
        )
        .where(
            Route.driver_id == principal.id,
            Route.status.in_([RouteStatus.PUBLISHED.value, RouteStatus.ACTIVE.value]),
        )
        .order_by(Route.created_at.desc())
    )
    if not route:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No active route")
    return {
        "id": route.id,
        "public_id": route.public_id,
        "version": route.version,
        "stops": [
            {
                "id": stop.id,
                "sequence": stop.sequence,
                "planned_at": stop.planned_at,
                "booking_reference": stop.booking.reference,
                "pickup_address": stop.booking.pickup_address,
                "packages": [
                    {
                        "id": package.id,
                        "retailer": package.retailer,
                        "status": package.status,
                        "version": package.version,
                    }
                    for package in stop.booking.packages
                ],
            }
            for stop in route.stops
        ],
    }


@router.post("/evidence/uploads", response_model=EvidenceView, status_code=201)
def create_evidence(
    data: EvidenceCreate,
    request: Request,
    db: DB,
    principal: Annotated[
        Principal, Depends(require_roles(Role.DRIVER, Role.DISPATCHER, Role.ADMIN))
    ],
) -> Evidence:
    package = db.scalar(
        select(Package).options(selectinload(Package.booking)).where(Package.id == data.package_id)
    )
    if not package:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Package not found")
    authorize_driver_package(db, principal, package)
    evidence = Evidence(
        package_id=package.id,
        kind=data.kind,
        storage_key=f"local/{package.id}/{data.checksum}",
        checksum=data.checksum,
        captured_at=data.captured_at,
        status="pending_upload",
        metadata_json={"content_type": data.content_type},
    )
    db.add(evidence)
    db.flush()
    audit(db, principal.id, "evidence.create", "evidence", evidence.id, request_id(request))
    db.commit()
    db.refresh(evidence)
    return evidence


@router.put("/evidence/{evidence_id}/content", response_model=EvidenceView)
async def upload_evidence(
    evidence_id: str,
    request: Request,
    file: UploadFile,
    db: DB,
    principal: Annotated[
        Principal, Depends(require_roles(Role.DRIVER, Role.DISPATCHER, Role.ADMIN))
    ],
) -> Evidence:
    evidence = db.get(Evidence, evidence_id)
    if not evidence:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evidence not found")
    package = db.scalar(
        select(Package)
        .options(selectinload(Package.booking))
        .where(Package.id == evidence.package_id)
    )
    assert package
    authorize_driver_package(db, principal, package)
    content = await file.read(5_000_001)
    if len(content) > 5_000_000:
        raise DomainError("evidence.too_large", "Evidence exceeds 5 MB.", 413)
    if file.content_type not in {"image/jpeg", "image/png", "application/pdf", "text/plain"}:
        raise DomainError("evidence.type_invalid", "Unsupported evidence type.", 422)
    settings = get_settings()
    destination = settings.upload_dir / evidence.storage_key
    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    Path(destination).write_bytes(content)
    evidence.status = "available"
    audit(db, principal.id, "evidence.upload", "evidence", evidence.id, request_id(request))
    db.commit()
    db.refresh(evidence)
    return evidence


def _package_for_driver(db: Session, package_id: str, principal: Principal) -> Package:
    package = db.scalar(
        select(Package)
        .options(selectinload(Package.booking).selectinload(Booking.packages))
        .where(Package.id == package_id)
    )
    if not package:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Package not found")
    authorize_driver_package(db, principal, package)
    return package


@router.post("/driver/packages/{package_id}:accept_pickup", response_model=PackageView)
def accept_pickup(
    package_id: str,
    data: CustodyCommand,
    request: Request,
    db: DB,
    principal: Annotated[
        Principal, Depends(require_roles(Role.DRIVER, Role.DISPATCHER, Role.ADMIN))
    ],
) -> Package:
    return custody_transition(
        db,
        _package_for_driver(db, package_id, principal),
        "accept_pickup",
        data,
        principal.id,
        request_id(request),
    )


@router.post("/driver/packages/{package_id}:record_handoff", response_model=PackageView)
def record_handoff(
    package_id: str,
    data: CustodyCommand,
    request: Request,
    db: DB,
    principal: Annotated[
        Principal, Depends(require_roles(Role.DRIVER, Role.DISPATCHER, Role.ADMIN))
    ],
) -> Package:
    return custody_transition(
        db,
        _package_for_driver(db, package_id, principal),
        "record_handoff",
        data,
        principal.id,
        request_id(request),
    )


@router.post("/driver/packages/{package_id}:exception", response_model=PackageView)
def package_exception(
    package_id: str,
    data: ExceptionCommand,
    request: Request,
    db: DB,
    principal: Annotated[
        Principal, Depends(require_roles(Role.DRIVER, Role.DISPATCHER, Role.ADMIN))
    ],
) -> Package:
    return record_exception(
        db, _package_for_driver(db, package_id, principal), data, principal.id, request_id(request)
    )


@router.get("/audit-events")
def list_audit(
    db: DB,
    _principal: Annotated[Principal, Depends(require_roles(Role.ADMIN, Role.SUPPORT))],
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict[str, object]]:
    events = db.scalars(
        select(AuditEvent).order_by(AuditEvent.occurred_at.desc()).limit(limit)
    ).all()
    return [
        {
            "id": e.id,
            "action": e.action,
            "resource_type": e.resource_type,
            "resource_id": e.resource_id,
            "occurred_at": e.occurred_at,
            "reason": e.reason,
        }
        for e in events
    ]


@router.post("/finance/bookings/{booking_id}/adjustments")
def create_adjustment(
    booking_id: str,
    data: FinancialAdjustment,
    request: Request,
    db: DB,
    principal: Annotated[Principal, Depends(require_roles(Role.FINANCE, Role.ADMIN))],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=120)],
) -> dict[str, object]:
    booking_query = (
        select(Booking)
        .options(selectinload(Booking.packages), selectinload(Booking.window))
        .where(Booking.id == booking_id)
    )
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        booking_query = booking_query.with_for_update()
    booking = db.scalar(booking_query)
    if not booking:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    prior = db.scalar(select(Payment).where(Payment.idempotency_key == idempotency_key))
    if prior:
        return {
            "id": prior.id,
            "kind": prior.kind,
            "status": prior.status,
            "amount_cents": prior.amount_cents,
        }
    if booking.version != data.expected_version:
        raise DomainError(
            "booking.version_conflict", "Booking changed; refresh before adjusting it."
        )
    if data.kind == "refund" and data.amount_cents > booking.total_cents:
        raise DomainError("payment.over_refund", "Refund exceeds the booking total.", 422)
    adjustment = Payment(
        booking_id=booking.id,
        provider="fake",
        provider_id=f"fake_adjustment_{secrets.token_hex(8)}",
        amount_cents=data.amount_cents,
        kind=data.kind,
        status="succeeded",
        idempotency_key=idempotency_key,
    )
    db.add(adjustment)
    if data.kind == "refund":
        booking.payment_status = (
            "refunded" if data.amount_cents == booking.total_cents else "partially_refunded"
        )
    booking.version += 1
    db.flush()
    add_outbox(
        db,
        f"payment.{data.kind}.succeeded.v1",
        "booking",
        booking.id,
        booking.version,
        {"booking_id": booking.id, "adjustment_id": adjustment.id},
        request_id(request),
    )
    audit(
        db,
        principal.id,
        f"payment.{data.kind}",
        "booking",
        booking.id,
        request_id(request),
        data.reason,
        amount_cents=data.amount_cents,
    )
    db.commit()
    return {
        "id": adjustment.id,
        "kind": adjustment.kind,
        "status": adjustment.status,
        "amount_cents": adjustment.amount_cents,
    }


@router.post("/webhooks/stripe")
def stripe_webhook(
    data: WebhookEvent,
    db: DB,
    x_returnet_signature: Annotated[str | None, Header()] = None,
) -> dict[str, bool]:
    settings = get_settings()
    if settings.payment_provider == "fake":
        if x_returnet_signature != "fake-local-webhook":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid fake webhook signature")
    else:
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED, "Stripe signature adapter is not configured"
        )
    existing = db.scalar(
        select(WebhookInbox).where(
            WebhookInbox.provider == "stripe", WebhookInbox.event_id == data.id
        )
    )
    if existing:
        return {"accepted": True, "duplicate": True}
    db.add(
        WebhookInbox(
            provider="stripe",
            event_id=data.id,
            event_type=data.type,
            payload=data.data,
            processed_at=now_utc(),
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"accepted": True, "duplicate": True}
    return {"accepted": True, "duplicate": False}
