from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.data.mongo import MongoRepository


class ReconciliationAuditService:
    """Append-only governance ledger for historical snapshot reconciliation."""

    def __init__(self) -> None:
        self.repository = MongoRepository("audit_ledger")

    def record(self, *, dataset_id: str, operation: str, key: str, loan_id: str, snapshot_date: str, actor: str = "system", reason: str = "", previous: dict[str, Any] | None = None, incoming: dict[str, Any] | None = None, changed_fields: list[str] | None = None) -> dict[str, Any]:
        entry = {
            "event_id": str(uuid4()),
            "event_type": "snapshot_reconciliation",
            "operation": operation,
            "dataset_id": dataset_id,
            "key": key,
            "loan_id": loan_id,
            "snapshot_date": snapshot_date,
            "actor": actor,
            "reason": reason,
            "changed_fields": changed_fields or [],
            "previous": previous or {},
            "incoming": incoming or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.repository.insert(entry)
        return entry

    def list(self, dataset_id: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
        filters = {"event_type": "snapshot_reconciliation"}
        if dataset_id:
            filters["dataset_id"] = dataset_id
        rows = self.repository.find(filters, limit=limit)
        rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
        return rows
