from hypothesis import given
from hypothesis import strategies as st

from backend.app.eta import EtaAlertState, evaluate_eta


def test_eta_thresholds_do_not_flap() -> None:
    state = EtaAlertState(route_version=1, last_eta_seconds=1_200)
    first = evaluate_eta(
        state,
        route_version=1,
        eta_seconds=850,
        confidence=0.9,
        location_age_seconds=10,
        driver_active=True,
    )
    assert first.event_type == "eta.approximately_15_minutes.v1"
    bounced = evaluate_eta(
        first.state,
        route_version=1,
        eta_seconds=910,
        confidence=0.9,
        location_age_seconds=10,
        driver_active=True,
    )
    again = evaluate_eta(
        bounced.state,
        route_version=1,
        eta_seconds=840,
        confidence=0.9,
        location_age_seconds=10,
        driver_active=True,
    )
    assert bounced.event_type is None and again.event_type is None
    final = evaluate_eta(
        again.state,
        route_version=1,
        eta_seconds=55,
        confidence=0.9,
        location_age_seconds=10,
        driver_active=True,
    )
    assert final.event_type == "eta.approximately_1_minute.v1"


@given(st.integers(min_value=0, max_value=900), st.floats(min_value=0, max_value=0.69))
def test_unreliable_eta_never_notifies(eta_seconds: int, confidence: float) -> None:
    result = evaluate_eta(
        EtaAlertState(route_version=1),
        route_version=1,
        eta_seconds=eta_seconds,
        confidence=confidence,
        location_age_seconds=10,
        driver_active=True,
    )
    assert result.event_type is None
