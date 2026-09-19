from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
import hashlib
import json

from app.data.mongo import MongoRepository


ACTION_LEVELS = {"low", "medium", "high"}
RECOMMENDATION_STATES = {
    "proposed",
    "pending_approval",
    "approved",
    "rejected",
    "executed",
    "cancelled",
    "expired",
}
RECOMMENDATION_ACTIONS = {"review", "limit_reduction", "preventive_block"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_evidence(evidence: dict[str, Any]) -> str:
    payload = json.dumps(evidence, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DecisionRecommendation:
    recommendation_id: str
    dataset_id: str
    loan_id: str | None
    action: str
    action_level: str
    status: str
    requires_human_approval: bool
    policy_id: str
    policy_version: int
    trigger_codes: tuple[str, ...]
    evidence: dict[str, Any]
    rationale: str
    source: str = "deterministic_ews"
    created_at: str = ""
    expires_at: str | None = None

    @classmethod
    def create(
        cls,
        *,
        dataset_id: str,
        action: str,
        action_level: str,
        policy_id: str,
        policy_version: int,
        evidence: dict[str, Any],
        rationale: str,
        loan_id: str | None = None,
        trigger_codes: list[str] | None = None,
        expires_at: str | None = None,
    ) -> "DecisionRecommendation":
        if action not in RECOMMENDATION_ACTIONS:
            raise ValueError(f"Unsupported recommendation action: {action}")
        if action_level not in ACTION_LEVELS:
            raise ValueError(f"Unsupported action level: {action_level}")
        requires_approval = action_level in {"medium", "high"}
        return cls(
            recommendation_id=str(uuid4()),
            dataset_id=dataset_id,
            loan_id=loan_id,
            action=action,
            action_level=action_level,
            status="pending_approval" if requires_approval else "proposed",
            requires_human_approval=requires_approval,
            policy_id=policy_id,
            policy_version=policy_version,
            trigger_codes=tuple(trigger_codes or []),
            evidence=dict(evidence),
            rationale=rationale,
            created_at=_now(),
            expires_at=expires_at,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "dataset_id": self.dataset_id,
            "loan_id": self.loan_id,
            "action": self.action,
            "action_level": self.action_level,
            "status": self.status,
            "requires_human_approval": self.requires_human_approval,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "trigger_codes": list(self.trigger_codes),
            "evidence": self.evidence,
            "evidence_hash": _hash_evidence(self.evidence),
            "rationale": self.rationale,
            "source": self.source,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "customer_action_executed": False,
        }


class DecisionRecommendationRepository:
    def __init__(self) -> None:
        self.collection = MongoRepository("decision_recommendations")
        self.ledger = MongoRepository("decision_ledger")
        self._indexes_ready = False

    def _ensure_indexes(self) -> None:
        if self._indexes_ready:
            return
        self.collection.ensure_indexes()
        self.collection.ensure_unique_index([("recommendation_id", 1)], name="recommendation_id_1")
        self.collection.ensure_unique_index([("dataset_id", 1), ("created_at", -1)], name="idx_recommendation_dataset_created")
        self.collection.ensure_unique_index([("status", 1), ("action_level", 1)], name="idx_recommendation_status_level")
        self.collection.ensure_unique_index([("loan_id", 1), ("created_at", -1)], name="idx_recommendation_loan_created")
        self.ledger.ensure_indexes()
        self.ledger.ensure_unique_index([("ledger_id", 1)], name="uniq_decision_ledger_id")
        self.ledger.ensure_unique_index([("recommendation_id", 1)], name="idx_decision_ledger_recommendation")
        self.ledger.ensure_unique_index([("dataset_id", 1), ("created_at", -1)], name="idx_decision_ledger_dataset_created")
        self._indexes_ready = True

    def save(self, recommendation: DecisionRecommendation) -> dict[str, Any]:
        self._ensure_indexes()
        document = recommendation.to_dict()
        existing = self.collection.find(
            {"recommendation_id": recommendation.recommendation_id},
            limit=1,
        )
        if existing:
            return existing[0]
        self.collection.insert(document)
        self._append_ledger(
            recommendation_id=recommendation.recommendation_id,
            dataset_id=recommendation.dataset_id,
            event="recommendation_proposed",
            actor="system",
            evidence=recommendation.evidence,
            state=recommendation.status,
        )
        return document

    def list(
        self,
        *,
        dataset_id: str | None = None,
        status: str | None = None,
        action_level: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        self._ensure_indexes()
        filters: dict[str, Any] = {}
        if dataset_id:
            filters["dataset_id"] = dataset_id
        if status:
            filters["status"] = status
        if action_level:
            filters["action_level"] = action_level
        rows = self.collection.find(filters, limit=max(1, min(limit, 500)))
        rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
        return rows

    def _append_ledger(
        self,
        *,
        recommendation_id: str,
        dataset_id: str,
        event: str,
        actor: str,
        evidence: dict[str, Any],
        state: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._ensure_indexes()
        evidence_snapshot = json.loads(json.dumps(evidence, default=str))
        ledger_id = str(uuid4())
        document = {
            "ledger_id": ledger_id,
            "recommendation_id": recommendation_id,
            "dataset_id": dataset_id,
            "event": event,
            "actor": actor,
            "state": state,
            "evidence_snapshot": evidence_snapshot,
            "evidence_hash": _hash_evidence(evidence_snapshot),
            "metadata": metadata or {},
            "created_at": _now(),
            "immutable": True,
        }
        self.ledger.insert(document)
        return document

    def transition(
        self,
        recommendation_id: str,
        *,
        status: str,
        actor: str = "user",
        comment: str = "",
    ) -> dict[str, Any]:
        """Transition a recommendation while preserving an immutable evidence ledger."""
        if status not in {"approved", "rejected"}:
            raise ValueError("status must be approved or rejected")
        self._ensure_indexes()
        rows = self.collection.find({"recommendation_id": recommendation_id}, limit=1)
        if not rows:
            raise KeyError(recommendation_id)
        current = rows[0]
        current_status = str(current.get("status") or "")
        if current_status not in {"pending_approval", "proposed"}:
            raise ValueError(f"recommendation is not reviewable from status {current_status}")
        if bool(current.get("requires_human_approval")) is False and status == "approved":
            raise ValueError("low-level recommendations do not require approval")

        metadata = {
            "comment": comment.strip(),
            "previous_status": current_status,
        }
        self.collection.update(
            {"recommendation_id": recommendation_id},
            {"$set": {
                "status": status,
                "reviewed_by": actor,
                "reviewed_at": _now(),
                "review_comment": comment.strip(),
            }},
        )
        self._append_ledger(
            recommendation_id=recommendation_id,
            dataset_id=str(current.get("dataset_id") or ""),
            event=f"recommendation_{status}",
            actor=actor,
            evidence=dict(current.get("evidence") or {}),
            state=status,
            metadata=metadata,
        )
        updated = self.collection.find({"recommendation_id": recommendation_id}, limit=1)
        return updated[0] if updated else {**current, "status": status, **metadata}

    def ledger_entries(
        self,
        *,
        dataset_id: str | None = None,
        recommendation_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        self._ensure_indexes()
        filters: dict[str, Any] = {}
        if dataset_id:
            filters["dataset_id"] = dataset_id
        if recommendation_id:
            filters["recommendation_id"] = recommendation_id
        rows = self.ledger.find(filters, limit=max(1, min(limit, 500)))
        rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
        return rows


class DecisionRecommendationEngine:
    """Deterministic action recommender.

    Gemini is deliberately outside this execution path. Recommendations are
    generated only from deterministic EWS evidence and versioned policy rules.
    """

    POLICY_ID = "ews-action-policy"
    POLICY_VERSION = 1

    def recommend(
        self,
        *,
        dataset_id: str,
        ews_summary: dict[str, Any],
        policy_id: str = POLICY_ID,
        policy_version: int = POLICY_VERSION,
    ) -> list[dict[str, Any]]:
        if not dataset_id:
            raise ValueError("dataset_id is required")
        if not ews_summary.get("available"):
            return []

        alerts = list(ews_summary.get("top_alerts") or [])
        recommendations: list[dict[str, Any]] = []

        for alert in alerts:
            score = float(alert.get("score") or 0)
            band = str(alert.get("band") or "normal")
            signals = list(alert.get("signals") or [])
            features = dict(alert.get("features") or {})
            trigger_codes = [str(item.get("code")) for item in signals if item.get("code")]

            if score >= 75 or band == "critical":
                action, level = "preventive_block", "high"
                rationale = (
                    "EWS determinístico clasifica la exposición como crítica. "
                    "La recomendación requiere aprobación humana antes de cualquier acción."
                )
            elif score >= 50 or band == "high":
                action, level = "limit_reduction", "medium"
                rationale = (
                    "EWS determinístico identifica deterioro relevante. "
                    "Se recomienda revisar/reducir exposición sujeto a aprobación humana."
                )
            elif score >= 25 or band == "watch":
                action, level = "review", "low"
                rationale = (
                    "EWS determinístico identifica una señal de vigilancia. "
                    "No se ejecuta ninguna acción sobre el cliente."
                )
            else:
                continue

            recommendation = DecisionRecommendation.create(
                dataset_id=dataset_id,
                loan_id=str(alert.get("loan_id") or "") or None,
                action=action,
                action_level=level,
                policy_id=policy_id,
                policy_version=policy_version,
                trigger_codes=trigger_codes,
                evidence={
                    "ews": alert,
                    "portfolio_as_of": ews_summary.get("as_of"),
                    "methodology": ews_summary.get("methodology"),
                    "predictive_probability": False,
                    "causality_inferred": False,
                },
                rationale=rationale,
            )
            recommendations.append(recommendation.to_dict())

        return recommendations
