from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pymongo import MongoClient
from pymongo.collection import Collection

from app.config import settings


class RiskAnalysisRepository:
    """Persistence adapter for immutable deterministic risk-analysis results."""

    COLLECTION_NAME = "risk_analysis_results"

    def __init__(
        self,
        client: MongoClient | None = None,
        database_name: str | None = None,
    ) -> None:
        self._client = client or MongoClient(settings.mongo_url, serverSelectionTimeoutMS=2000)
        self._db = self._client[database_name or settings.mongo_db]
        self._collection: Collection = self._db[self.COLLECTION_NAME]

    def save_analysis(
        self,
        dataset_id: str,
        payload: dict[str, Any],
        engine_version: str = "1.0.0",
    ) -> str:
        """Persist one canonical analysis result and return its stable result_id."""
        result_id = str(uuid4())
        migration = payload.get("migration") or {}
        integrity = payload.get("integrity") or {}

        document: dict[str, Any] = {
            "result_id": result_id,
            "dataset_id": dataset_id,
            "calculated_at": datetime.now(timezone.utc),
            "engine_version": engine_version,
            "t0_snapshot": migration.get("t0"),
            "t1_snapshot": migration.get("t1"),
            "integrity_status": integrity.get("status", "unknown"),
            "payload": payload,
        }
        self._collection.insert_one(document)
        return result_id

    def get_analysis_by_id(self, result_id: str) -> dict[str, Any] | None:
        """Return a persisted analysis by result_id, or None when absent."""
        document = self._collection.find_one({"result_id": result_id})
        if document is None:
            return None
        return self._normalize_document(document)

    def list_analyses_by_dataset(
        self,
        dataset_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Return the most recent persisted analyses for a dataset."""
        safe_limit = max(1, min(limit, 100))
        documents = (
            self._collection.find({"dataset_id": dataset_id})
            .sort("calculated_at", -1)
            .limit(safe_limit)
        )
        return [self._normalize_document(document) for document in documents]

    @staticmethod
    def _normalize_document(document: dict[str, Any]) -> dict[str, Any]:
        """Convert Mongo-specific fields into API-safe audit metadata."""
        result = dict(document)
        result.pop("_id", None)
        calculated_at = result.get("calculated_at")
        if isinstance(calculated_at, datetime):
            result["calculated_at"] = calculated_at.astimezone(timezone.utc).isoformat()
        return result
