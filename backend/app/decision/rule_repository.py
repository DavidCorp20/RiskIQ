from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.data.mongo import MongoRepository


class DecisionRuleRepository:
    """Mongo persistence for reusable low-code decision rules.

    Governance is append-only: once a policy version reaches APPROVED or
    DEPLOYED, the version cannot be overwritten. Changes must be created as a
    new version through the governance clone flow.
    """

    def __init__(self) -> None:
        self.rules = MongoRepository("decision_rules")
        self.governance_events = MongoRepository("policy_governance_events")

    @staticmethod
    def _version(rule: dict[str, Any]) -> int:
        package = rule.get("policy_package") or {}
        return int(rule.get("version") or package.get("version") or 1)

    @staticmethod
    def _policy_id(rule: dict[str, Any]) -> str:
        package = rule.get("policy_package") or {}
        return str(rule.get("id") or package.get("policy_id") or "")

    def _effective_status(self, rule: dict[str, Any]) -> str:
        package = rule.get("policy_package") or {}
        status = str(package.get("status") or rule.get("status") or "DRAFT").upper()
        policy_id = self._policy_id(rule)
        version = self._version(rule)
        if policy_id:
            events = self.governance_events.find({"policy_id": policy_id, "version": version}, limit=1000)
            if events:
                events.sort(key=lambda x: str(x.get("at") or x.get("created_at") or ""))
                status = str(events[-1].get("to") or status).upper()
        return status

    def save(self, rule: dict[str, Any], dataset_id: str | None = None, business_id: str | None = None) -> dict[str, Any]:
        document = {**rule, "dataset_id": dataset_id, "business_id": business_id, "saved_at": datetime.now(timezone.utc).isoformat()}
        document.pop("_id", None)

        policy_id = self._policy_id(document)
        version = self._version(document)
        existing = self.rules.find({"id": policy_id, "version": version}, limit=1) if policy_id else []
        if existing:
            current_status = self._effective_status(existing[0])
            if current_status in {"APPROVED", "DEPLOYED", "RETIRED"}:
                raise HTTPException(
                    status_code=409,
                    detail=f"Policy version {policy_id} v{version} is immutable in status {current_status}; clone it to create a new version.",
                )

        self.rules.insert(document)
        return document

    def list(self, dataset_id: str | None = None, business_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        filters: dict[str, Any] = {}
        if dataset_id: filters["dataset_id"] = dataset_id
        if business_id: filters["business_id"] = business_id
        return self.rules.find(filters, limit=limit)
