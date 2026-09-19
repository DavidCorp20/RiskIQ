from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from enum import Enum


class LifecycleStatus(str, Enum):
    DETECTED = "DETECTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INVESTIGATING = "INVESTIGATING"
    ACTIONED = "ACTIONED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


ALLOWED_TRANSITIONS = {
    LifecycleStatus.DETECTED: {LifecycleStatus.ACKNOWLEDGED},
    LifecycleStatus.ACKNOWLEDGED: {LifecycleStatus.INVESTIGATING},
    LifecycleStatus.INVESTIGATING: {LifecycleStatus.ACTIONED},
    LifecycleStatus.ACTIONED: {LifecycleStatus.RESOLVED},
    LifecycleStatus.RESOLVED: {LifecycleStatus.CLOSED},
    LifecycleStatus.CLOSED: set(),
}


@dataclass(frozen=True)
class RiskEventLifecycle:
    event_key: str
    status: LifecycleStatus = LifecycleStatus.DETECTED
    severity: str = "LOW"
    confidence: float = 0.0
    expected_financial_impact: float = 0.0
    owner_id: str | None = None
    sla_deadline_utc: datetime | None = None
    resolution_notes: str | None = None
    recurrence_count: int = 0


SLA_HOURS = {"LOW": 72, "MEDIUM": 48, "HIGH": 24, "CRITICAL": 8}


def sla_deadline(severity: str, now: datetime | None = None) -> datetime:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current + timedelta(hours=SLA_HOURS.get(str(severity).upper(), 72))


def transition(event: RiskEventLifecycle, target: LifecycleStatus) -> RiskEventLifecycle:
    if target not in ALLOWED_TRANSITIONS[event.status]:
        raise ValueError(f"Invalid EWS transition: {event.status.value} -> {target.value}")
    return replace(event, status=target)


def apply_recurrence(
    event: RiskEventLifecycle,
    prior_event_keys: set[str],
    escalation_map: dict[str, str] | None = None,
) -> RiskEventLifecycle:
    recurring = event.event_key in prior_event_keys
    if not recurring:
        return event
    mapping = escalation_map or {"LOW": "MEDIUM", "MEDIUM": "HIGH", "HIGH": "CRITICAL"}
    severity = mapping.get(event.severity.upper(), event.severity.upper())
    return replace(event, severity=severity, recurrence_count=event.recurrence_count + 1)
