from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.data.mongo import MongoRepository
from app.risk_events.models import RiskAction


class InternalTaskAdapter:
    """Native Mongo-backed mitigation task adapter."""

    def __init__(self, repository: MongoRepository | None = None) -> None:
        self.repository = repository or MongoRepository("internal_risk_tasks")
        self.ready = False

    def _ensure(self) -> None:
        if self.ready:
            return
        self.repository.ensure_indexes()
        self.repository.ensure_unique_index([("action_id", 1)], name="uniq_internal_risk_action")
        self.ready = True

    async def dispatch(self, action: RiskAction | dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
        self._ensure()
        row = action.model_dump(mode="json") if isinstance(action, RiskAction) else dict(action)
        existing = self.repository.find({"action_id": row["action_id"]}, limit=1)
        if existing:
            return {"enabled": True, "adapter": "INTERNAL", "created": False, "task_id": existing[0].get("task_id"), "action_id": row["action_id"]}

        now = datetime.now(timezone.utc).isoformat()
        document = {
            "task_id": row["action_id"],
            "action_id": row["action_id"],
            "event_id": row.get("event_id"),
            "dataset_id": event.get("dataset_id"),
            "event_type": event.get("event_type"),
            "severity": event.get("severity"),
            "status": row.get("status", "PENDING"),
            "priority": row.get("priority", 3),
            "owner": row.get("owner", "risk_analyst"),
            "rationale": row.get("rationale", ""),
            "evidence": row.get("evidence") or event.get("evidence") or {},
            "due_at": row.get("due_at"),
            "created_at": now,
            "updated_at": now,
        }
        self.repository.insert(document)
        return {"enabled": True, "adapter": "INTERNAL", "created": True, "task_id": row["action_id"], "action_id": row["action_id"]}
