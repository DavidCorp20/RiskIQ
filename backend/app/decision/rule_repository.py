from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.data.mongo import MongoRepository


class DecisionRuleRepository:
    """Mongo persistence for reusable low-code decision rules."""

    def __init__(self) -> None:
        self.rules = MongoRepository("decision_rules")

    def save(self, rule: dict[str, Any], dataset_id: str | None = None, business_id: str | None = None) -> dict[str, Any]:
        document = {**rule, "dataset_id": dataset_id, "business_id": business_id, "saved_at": datetime.now(timezone.utc).isoformat()}
        document.pop("_id", None)
        self.rules.insert(document)
        return document

    def list(self, dataset_id: str | None = None, business_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        filters: dict[str, Any] = {}
        if dataset_id: filters["dataset_id"] = dataset_id
        if business_id: filters["business_id"] = business_id
        return self.rules.find(filters, limit=limit)
