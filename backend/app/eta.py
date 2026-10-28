from dataclasses import dataclass


@dataclass(frozen=True)
class EtaAlertState:
    route_version: int
    sent_15_minute: bool = False
    sent_1_minute: bool = False
    last_eta_seconds: int | None = None


@dataclass(frozen=True)
class EtaDecision:
    event_type: str | None
    state: EtaAlertState


def evaluate_eta(
    state: EtaAlertState,
    *,
    route_version: int,
    eta_seconds: int,
    confidence: float,
    location_age_seconds: int,
    driver_active: bool,
) -> EtaDecision:
    """Choose at most one alert using confidence, staleness and threshold hysteresis."""
    if route_version != state.route_version:
        state = EtaAlertState(route_version=route_version)
    reliable = confidence >= 0.7 and location_age_seconds <= 120 and driver_active
    event: str | None = None
    downward = state.last_eta_seconds is None or eta_seconds < state.last_eta_seconds
    if reliable and downward:
        if eta_seconds <= 60 and not state.sent_1_minute:
            event = "eta.approximately_1_minute.v1"
        elif eta_seconds <= 900 and not state.sent_15_minute:
            event = "eta.approximately_15_minutes.v1"
    updated = EtaAlertState(
        route_version=route_version,
        sent_15_minute=state.sent_15_minute or event == "eta.approximately_15_minutes.v1",
        sent_1_minute=state.sent_1_minute or event == "eta.approximately_1_minute.v1",
        last_eta_seconds=eta_seconds,
    )
    return EtaDecision(event, updated)
