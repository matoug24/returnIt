from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AddressInput(BaseModel):
    line1: str = Field(min_length=3, max_length=160)
    city: str = "Montréal"
    province: Literal["QC"] = "QC"
    postal_code: str = Field(pattern=r"^[A-Za-z]\d[A-Za-z][ -]?\d[A-Za-z]\d$")
    access_notes: str | None = Field(default=None, max_length=500)
    latitude: float = Field(ge=45.35, le=45.75)
    longitude: float = Field(ge=-74.05, le=-73.35)


class PackageInput(BaseModel):
    retailer: str = Field(min_length=1, max_length=120)
    carrier: str = Field(min_length=1, max_length=120)
    label_code: str = Field(min_length=3, max_length=160)
    destination_name: str = Field(min_length=2, max_length=160)
    destination_address: str = Field(min_length=3, max_length=300)
    destination_open_until: datetime
    weight_grams: int = Field(gt=0, le=20000)


class BookingCreate(BaseModel):
    window_id: str
    pickup_address: AddressInput
    preferred_at: datetime | None = None
    packages: list[PackageInput] = Field(min_length=1, max_length=5)
    payment_method: Literal["fake_card", "subscription"] = "fake_card"
    accepted_terms_version: Literal["pilot-v1"]
    package_attestation: Literal[True]


class BookingView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    reference: str
    status: str
    locale: str
    pickup_address: dict[str, Any]
    preferred_at: datetime | None
    subtotal_cents: int
    tax_cents: int
    total_cents: int
    payment_status: str
    version: int
    packages: list["PackageView"]


class PackageView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    ordinal: int
    retailer: str
    carrier: str
    destination_name: str
    status: str
    version: int


class WindowView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    zone: str
    starts_at: datetime
    ends_at: datetime
    capacity: int
    reserved: int
    version: int


class RoutePlanRequest(BaseModel):
    service_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    driver_id: str
    shift_start: datetime
    shift_end: datetime
    capacity_grams: int = Field(default=100_000, gt=0)
    break_minutes: int = Field(default=30, ge=0, le=120)

    @model_validator(mode="after")
    def valid_shift(self) -> "RoutePlanRequest":
        if self.shift_end <= self.shift_start:
            raise ValueError("shift_end must be after shift_start")
        return self


class RouteView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    public_id: str
    driver_id: str
    service_date: str
    status: str
    version: int
    plan: dict[str, Any]
    published_at: datetime | None
    stops: list["StopView"]


class StopView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    booking_id: str
    sequence: int
    kind: str
    planned_at: datetime
    service_minutes: int
    status: str


class PublishRoute(BaseModel):
    expected_version: int
    reason: str = Field(min_length=3, max_length=200)


class CustodyCommand(BaseModel):
    command_id: str = Field(min_length=8, max_length=120)
    expected_version: int
    occurred_at: datetime
    evidence_ids: list[str] = Field(default_factory=list)
    reason: str | None = Field(default=None, max_length=120)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    tracking_reference: str | None = Field(default=None, max_length=160)


class EvidenceCreate(BaseModel):
    package_id: str
    kind: Literal["photo", "scan", "receipt", "tracking_reference"]
    checksum: str = Field(min_length=8, max_length=128)
    captured_at: datetime
    content_type: str = Field(default="image/jpeg", max_length=80)


class EvidenceView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    package_id: str
    kind: str
    storage_key: str
    checksum: str
    status: str
    captured_at: datetime


class ExceptionCommand(BaseModel):
    command_id: str = Field(min_length=8, max_length=120)
    expected_version: int
    occurred_at: datetime
    reason: Literal[
        "customer_no_show",
        "invalid_label",
        "rejected_package",
        "driver_delay",
        "destination_closed",
        "destination_rejected",
        "lost",
        "damaged",
    ]
    evidence_ids: list[str] = Field(default_factory=list)


class BookingAction(BaseModel):
    expected_version: int
    reason: str = Field(min_length=3, max_length=200)


class RescheduleAction(BookingAction):
    window_id: str
    preferred_at: datetime | None = None


class FinancialAdjustment(BaseModel):
    expected_version: int
    kind: Literal["refund", "credit"]
    amount_cents: int = Field(gt=0)
    reason: str = Field(min_length=3, max_length=200)


class WebhookEvent(BaseModel):
    id: str
    type: str
    data: dict[str, Any]


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str
