from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class DecisionHistoryEntry:
    decision_id: str
    decision_code: str
    title: str
    status: str
    mode: str
    evidence: dict[str, Any]
    recommendation: str
    rationale: str
    actor: str = "system"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    outcome: dict[str, Any] | None = None

    @classmethod
    def create(cls, decision: dict[str, Any], actor: str = "system") -> "DecisionHistoryEntry":
        return cls(
            decision_id=str(decision.get("id") or uuid4()),
            decision_code=str(decision.get("code") or decision.get("category") or "UNKNOWN"),
            title=str(decision.get("title") or "Risk decision"),
            status=str(decision.get("status") or "proposed"),
            mode=str(decision.get("mode") or "suggested"),
            evidence=dict(decision.get("evidence") or {}),
            recommendation=str(decision.get("recommendation") or decision.get("title") or ""),
            rationale=str(decision.get("rationale") or ""),
            actor=actor,
        )

    def with_outcome(self, outcome: dict[str, Any]) -> "DecisionHistoryEntry":
        return DecisionHistoryEntry(
            decision_id=self.decision_id,
            decision_code=self.decision_code,
            title=self.title,
            status="resolved",
            mode=self.mode,
            evidence=self.evidence,
            recommendation=self.recommendation,
            rationale=self.rationale,
            actor=self.actor,
            created_at=self.created_at,
            outcome=dict(outcome),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "decision_code": self.decision_code,
            "title": self.title,
            "status": self.status,
            "mode": self.mode,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "rationale": self.rationale,
            "actor": self.actor,
            "created_at": self.created_at,
            "outcome": self.outcome,
        }


class DecisionHistoryService:
    """In-memory MVP audit trail; persistence can be replaced by Mongo/PostgreSQL later."""

    def __init__(self) -> None:
        self._entries: dict[str, DecisionHistoryEntry] = {}

    def record(self, decision: dict[str, Any], actor: str = "system") -> dict[str, Any]:
        entry = DecisionHistoryEntry.create(decision, actor)
        self._entries[entry.decision_id] = entry
        return entry.to_dict()

    def resolve(self, decision_id: str, outcome: dict[str, Any]) -> dict[str, Any]:
        entry = self._entries.get(decision_id)
        if entry is None:
            raise KeyError(decision_id)
        updated = entry.with_outcome(outcome)
        self._entries[decision_id] = updated
        return updated.to_dict()

    def list(self, status: str | None = None) -> list[dict[str, Any]]:
        entries = list(self._entries.values())
        if status:
            entries = [entry for entry in entries if entry.status == status]
        entries.sort(key=lambda item: item.created_at, reverse=True)
        return [entry.to_dict() for entry in entries]
