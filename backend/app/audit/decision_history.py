from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.data.mongo import MongoRepository


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
    dataset_id: str | None = None
    snapshot_id: str | None = None
    policy_id: str | None = None
    policy_version: str | None = None
    backtest_id: str | None = None
    business_id: str | None = None

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
            dataset_id=_optional(decision.get("dataset_id")),
            snapshot_id=_optional(decision.get("snapshot_id")),
            policy_id=_optional(decision.get("policy_id")),
            policy_version=_optional(decision.get("policy_version") or decision.get("policy_version_id")),
            backtest_id=_optional(decision.get("backtest_id")),
            business_id=_optional(decision.get("business_id")),
        )

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "DecisionHistoryEntry":
        return cls(
            decision_id=str(value.get("decision_id")),
            decision_code=str(value.get("decision_code") or "UNKNOWN"),
            title=str(value.get("title") or "Risk decision"),
            status=str(value.get("status") or "proposed"),
            mode=str(value.get("mode") or "suggested"),
            evidence=dict(value.get("evidence") or {}),
            recommendation=str(value.get("recommendation") or ""),
            rationale=str(value.get("rationale") or ""),
            actor=str(value.get("actor") or "system"),
            created_at=str(value.get("created_at") or datetime.now(timezone.utc).isoformat()),
            outcome=dict(value["outcome"]) if value.get("outcome") is not None else None,
            dataset_id=_optional(value.get("dataset_id")),
            snapshot_id=_optional(value.get("snapshot_id")),
            policy_id=_optional(value.get("policy_id")),
            policy_version=_optional(value.get("policy_version")),
            backtest_id=_optional(value.get("backtest_id")),
            business_id=_optional(value.get("business_id")),
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
            dataset_id=self.dataset_id,
            snapshot_id=self.snapshot_id,
            policy_id=self.policy_id,
            policy_version=self.policy_version,
            backtest_id=self.backtest_id,
            business_id=self.business_id,
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
            "dataset_id": self.dataset_id,
            "snapshot_id": self.snapshot_id,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "backtest_id": self.backtest_id,
            "business_id": self.business_id,
        }


def _optional(value: Any) -> str | None:
    return str(value) if value not in (None, "") else None


class DecisionHistoryService:
    """Mongo-backed decision evidence ledger with the existing audit API contract."""

    def __init__(self) -> None:
        self.repository = MongoRepository("decision_history")
        self.repository.ensure_indexes()
        self.repository._collection.create_index([("decision_id", 1)], unique=True)
        self.repository._collection.create_index([("policy_id", 1), ("policy_version", 1)])

    def record(self, decision: dict[str, Any], actor: str = "system") -> dict[str, Any]:
        entry = DecisionHistoryEntry.create(decision, actor)
        existing = self.repository.find({"decision_id": entry.decision_id}, limit=1)
        if existing:
            return existing[0]
        document = entry.to_dict()
        self.repository.insert(document)
        return document

    def resolve(self, decision_id: str, outcome: dict[str, Any]) -> dict[str, Any]:
        rows = self.repository.find({"decision_id": decision_id}, limit=1)
        if not rows:
            raise KeyError(decision_id)
        updated = DecisionHistoryEntry.from_dict(rows[0]).with_outcome(outcome)
        self.repository.update({"decision_id": decision_id}, {"$set": updated.to_dict()})
        return updated.to_dict()

    def list(self, status: str | None = None, dataset_id: str | None = None) -> list[dict[str, Any]]:
        filters: dict[str, Any] = {}
        if status:
            filters["status"] = status
        if dataset_id:
            filters["dataset_id"] = dataset_id
        entries = self.repository.find(filters, limit=500)
        entries.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return entries
