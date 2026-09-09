from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, MongoClient

from app.config import settings


class MongoRepository:
    """Small persistence adapter so domain services stay database-agnostic."""

    def __init__(self, collection: str):
        self.collection_name = collection
        self._client = MongoClient(settings.mongo_url, serverSelectionTimeoutMS=3000)
        self._collection = self._client[settings.mongo_db][collection]

    def ping(self) -> bool:
        self._client.admin.command("ping")
        return True

    def ensure_indexes(self) -> None:
        self._collection.create_index([("business_id", ASCENDING)])
        self._collection.create_index([("created_at", ASCENDING)])
        self._collection.create_index([("dataset_id", ASCENDING)])

    def insert(self, document: dict[str, Any]) -> str:
        payload = dict(document)
        payload.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        result = self._collection.insert_one(payload)
        return str(result.inserted_id)

    def find(self, filters: dict[str, Any] | None = None, limit: int = 100) -> list[dict[str, Any]]:
        rows = list(self._collection.find(filters or {}, {"_id": 0}).limit(limit))
        return rows

    def close(self) -> None:
        self._client.close()
