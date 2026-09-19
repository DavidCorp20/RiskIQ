from datetime import datetime, timezone
import pytest
from app.risk_events.lifecycle import LifecycleStatus, RiskEventLifecycle, apply_recurrence, sla_deadline, transition


def test_valid_lifecycle_transitions():
    event = RiskEventLifecycle(event_key="k")
    for target in (
        LifecycleStatus.ACKNOWLEDGED,
        LifecycleStatus.INVESTIGATING,
        LifecycleStatus.ACTIONED,
        LifecycleStatus.RESOLVED,
        LifecycleStatus.CLOSED,
    ):
        event = transition(event, target)
    assert event.status is LifecycleStatus.CLOSED


def test_invalid_transition_is_rejected():
    with pytest.raises(ValueError):
        transition(RiskEventLifecycle(event_key="k"), LifecycleStatus.RESOLVED)


def test_sla_deadline_is_deterministic():
    now = datetime(2026, 9, 19, tzinfo=timezone.utc)
    assert (sla_deadline("CRITICAL", now) - now).total_seconds() == 8 * 3600


def test_recurrence_escalates_severity():
    event = RiskEventLifecycle(event_key="k", severity="HIGH")
    result = apply_recurrence(event, {"k"})
    assert result.severity == "CRITICAL"
    assert result.recurrence_count == 1
