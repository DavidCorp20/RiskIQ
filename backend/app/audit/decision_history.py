from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.data.mongo import MongoRepository


class DecisionHistoryEntry:
    """Normalized evidence-ledger record for a decision."""

    def __init__(self, **kwargs: Any) -> None:
        self.__dict__.update(kwargs)

    @classmethod
    def create(cls, decision: dict[str, Any], actor: str = "system") -> "DecisionHistoryEntry":
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            decision_id=str(decision.get("decision_id") or uuid4()),
            created_at=now,
            actor=actor,
            decision_type=decision.get("decision_type") or decision.get("type") or "risk_review",
            title=decision.get("title") or decision.get("name") or "Risk decision",
            rationale=decision.get("rationale") or decision.get("reason") or "",
            status=decision.get("status") or "pending_review",
            outcome=decision.get("outcome"),
            dataset_id=_optional(decision.get("dataset_id")),
            snapshot_id=_optional(decision.get("snapshot_id")),
            policy_id=_optional(decision.get("policy_id")),
            policy_version=_optional(decision.get("policy_version")),
            backtest_id=_optional(decision.get("backtest_id")),
            business_id=_optional(decision.get("business_id")),
        )

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "DecisionHistoryEntry":
        return cls(**row)

    def with_outcome(self, outcome: dict[str, Any]) -> "DecisionHistoryEntry":
        payload = dict(self.__dict__)
        payload["outcome"] = outcome
        payload["status"] = "resolved"
        return type(self)(**payload)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def _optional(value: Any) -> str | None:
    return str(value) if value not in (None, "") else None


class DecisionHistoryService:
    """Mongo-backed decision evidence ledger with lazy index initialization.

    Importing the API must not require MongoDB to be running. This matters for
    CI, local frontend work and health/read-only startup paths. Indexes are
    created on the first persistence operation instead.
    """

    def __init__(self) -> None:
        self.repository = MongoRepository("decision_history")
        self._indexes_ready = False

    def _ensure_indexes(self) -> None:
        if self._indexes_ready:
            return
        self.repository.ensure_indexes()
        self.repository._collection.create_index([("decision_id", 1)], unique=True)
        self.repository._collection.create_index([("policy_id", 1), ("policy_version", 1)])
        self._indexes_ready = True

    def record(self, decision: dict[str, Any], actor: str = "system") -> dict[str, Any]:
        self._ensure_indexes()
        entry = DecisionHistoryEntry.create(decision, actor)
        existing = self.repository.find({"decision_id": entry.decision_id}, limit=1)
        if existing:
            return existing[0]
        document = entry.to_dict()
        self.repository.insert(document)
        return document

    def resolve(self, decision_id: str, outcome: dict[str, Any]) -> dict[str, Any]:
        self._ensure_indexes()
        rows = self.repository.find({"decision_id": decision_id}, limit=1)
        if not rows:
            raise KeyError(decision_id)
        updated = DecisionHistoryEntry.from_dict(rows[0]).with_outcome(outcome)
        self.repository.update({"decision_id": decision_id}, {"$set": updated.to_dict()})
        return updated.to_dict()
