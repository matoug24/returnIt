from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def new_id() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.now(UTC)


class Role(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    DRIVER = "DRIVER"
    DISPATCHER = "DISPATCHER"
    ADMIN = "ADMIN"
    SUPPORT = "SUPPORT"
    FINANCE = "FINANCE"


class BookingStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    SCHEDULED = "scheduled"
    ROUTE_LOCKED = "route_locked"
    IN_PROGRESS = "in_progress"
    PARTIALLY_COMPLETED = "partially_completed"
    COMPLETED = "completed"
    EXCEPTION = "exception"
    CANCELLED = "cancelled"


class PackageStatus(str, enum.Enum):
    EXPECTED = "expected"
    PICKUP_ATTEMPTED = "pickup_attempted"
    IN_CUSTODY = "in_custody"
    NOT_COLLECTED = "not_collected"
    AT_DESTINATION_ATTEMPT = "at_destination_attempt"
    HANDED_OFF = "handed_off"
    IN_CUSTODY_EXCEPTION = "in_custody_exception"
    RETURNED_TO_CUSTOMER = "returned_to_customer"
    CLAIM_RESOLVED = "claim_resolved"
    PROOF_DISPUTED = "proof_disputed"


class RouteStatus(str, enum.Enum):
    PROPOSED = "proposed"
    PUBLISHED = "published"
    ACTIVE = "active"
    PARTIALLY_COMPLETED = "partially_completed"
    COMPLETED = "completed"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, onupdate=now_utc
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(24), index=True)
    locale: Mapped[str] = mapped_column(String(8), default="en-CA")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ServiceWindow(Base, TimestampMixin):
    __tablename__ = "service_windows"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    zone: Mapped[str] = mapped_column(String(80), default="Montreal Core")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    capacity: Mapped[int] = mapped_column(Integer, default=10)
    reserved: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)


class Booking(Base, TimestampMixin):
    __tablename__ = "bookings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    reference: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    window_id: Mapped[str] = mapped_column(ForeignKey("service_windows.id"), index=True)
    pickup_address: Mapped[dict[str, Any]] = mapped_column(JSON)
    preferred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default=BookingStatus.CONFIRMED.value)
    locale: Mapped[str] = mapped_column(String(8), default="en-CA")
    subtotal_cents: Mapped[int] = mapped_column(Integer)
    tax_cents: Mapped[int] = mapped_column(Integer)
    total_cents: Mapped[int] = mapped_column(Integer)
    payment_status: Mapped[str] = mapped_column(String(32), default="paid")
    version: Mapped[int] = mapped_column(Integer, default=1)
    route_id: Mapped[str | None] = mapped_column(ForeignKey("routes.id"), nullable=True)
    customer: Mapped[User] = relationship(foreign_keys=[customer_id])
    window: Mapped[ServiceWindow] = relationship()
    packages: Mapped[list[Package]] = relationship(
        back_populates="booking", cascade="all, delete-orphan", order_by="Package.ordinal"
    )


class Package(Base, TimestampMixin):
    __tablename__ = "packages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    booking_id: Mapped[str] = mapped_column(ForeignKey("bookings.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    retailer: Mapped[str] = mapped_column(String(120))
    carrier: Mapped[str] = mapped_column(String(120))
    label_code: Mapped[str] = mapped_column(String(160))
    destination_name: Mapped[str] = mapped_column(String(160))
    destination_address: Mapped[str] = mapped_column(String(300))
    destination_open_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    weight_grams: Mapped[int] = mapped_column(Integer, default=1000)
    status: Mapped[str] = mapped_column(String(40), default=PackageStatus.EXPECTED.value)
    version: Mapped[int] = mapped_column(Integer, default=1)
    booking: Mapped[Booking] = relationship(back_populates="packages")

    __table_args__ = (UniqueConstraint("booking_id", "ordinal"),)


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    booking_id: Mapped[str] = mapped_column(ForeignKey("bookings.id"), index=True)
    provider: Mapped[str] = mapped_column(String(30))
    provider_id: Mapped[str] = mapped_column(String(120), unique=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(32), default="charge")
    status: Mapped[str] = mapped_column(String(32))
    idempotency_key: Mapped[str] = mapped_column(String(120), unique=True)


class Route(Base, TimestampMixin):
    __tablename__ = "routes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    public_id: Mapped[str] = mapped_column(String(20), unique=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    service_date: Mapped[str] = mapped_column(String(10), index=True)
    status: Mapped[str] = mapped_column(String(32), default=RouteStatus.PROPOSED.value)
    version: Mapped[int] = mapped_column(Integer, default=1)
    input_hash: Mapped[str] = mapped_column(String(64))
    plan: Mapped[dict[str, Any]] = mapped_column(JSON)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    driver: Mapped[User] = relationship()
    stops: Mapped[list[Stop]] = relationship(
        back_populates="route", cascade="all, delete-orphan", order_by="Stop.sequence"
    )


class Stop(Base, TimestampMixin):
    __tablename__ = "stops"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    route_id: Mapped[str] = mapped_column(ForeignKey("routes.id"), index=True)
    booking_id: Mapped[str] = mapped_column(ForeignKey("bookings.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(30), default="pickup")
    planned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    service_minutes: Mapped[int] = mapped_column(Integer, default=8)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    route: Mapped[Route] = relationship(back_populates="stops")
    booking: Mapped[Booking] = relationship(foreign_keys=[booking_id])


class CustodyEvent(Base):
    __tablename__ = "custody_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    package_id: Mapped[str] = mapped_column(ForeignKey("packages.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(60))
    from_status: Mapped[str] = mapped_column(String(40))
    to_status: Mapped[str] = mapped_column(String(40))
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    command_id: Mapped[str] = mapped_column(String(120), unique=True)
    reason: Mapped[str | None] = mapped_column(String(120))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    __table_args__ = (UniqueConstraint("package_id", "sequence"),)


class Evidence(Base, TimestampMixin):
    __tablename__ = "evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    package_id: Mapped[str] = mapped_column(ForeignKey("packages.id"), index=True)
    custody_event_id: Mapped[str | None] = mapped_column(ForeignKey("custody_events.id"))
    kind: Mapped[str] = mapped_column(String(30))
    storage_key: Mapped[str] = mapped_column(String(300))
    checksum: Mapped[str] = mapped_column(String(128))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="available")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    booking_id: Mapped[str] = mapped_column(ForeignKey("bookings.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(60))
    channel: Mapped[str] = mapped_column(String(20))
    locale: Mapped[str] = mapped_column(String(8))
    dedupe_key: Mapped[str] = mapped_column(String(180), unique=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    aggregate_type: Mapped[str] = mapped_column(String(40))
    aggregate_id: Mapped[str] = mapped_column(String(36), index=True)
    aggregate_version: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    correlation_id: Mapped[str] = mapped_column(String(80), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(500))


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    actor_id: Mapped[str] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    resource_type: Mapped[str] = mapped_column(String(40))
    resource_id: Mapped[str] = mapped_column(String(36), index=True)
    reason: Mapped[str | None] = mapped_column(String(200))
    request_id: Mapped[str] = mapped_column(String(80), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    principal_id: Mapped[str] = mapped_column(String(36))
    operation: Mapped[str] = mapped_column(String(100))
    key: Mapped[str] = mapped_column(String(120))
    request_hash: Mapped[str] = mapped_column(String(64))
    response_status: Mapped[int] = mapped_column(Integer)
    response_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    __table_args__ = (UniqueConstraint("principal_id", "operation", "key"),)


class WebhookInbox(Base):
    __tablename__ = "webhook_inbox"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    provider: Mapped[str] = mapped_column(String(30))
    event_id: Mapped[str] = mapped_column(String(160))
    event_type: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (UniqueConstraint("provider", "event_id"),)
