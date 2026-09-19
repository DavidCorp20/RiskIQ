from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pymongo import ASCENDING, MongoClient

from app.config import settings


def _bson_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: _bson_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_bson_safe(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_bson_safe(item) for item in value)
    return value


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

    def ensure_index(
        self,
        fields: list[tuple[str, int]],
        *,
        name: str | None = None,
        unique: bool = False,
    ) -> None:
        """Create an index with explicit uniqueness semantics."""
        self._collection.create_index(fields, unique=unique, name=name)

    def ensure_indexes_for(
        self,
        indexes: list[tuple[list[tuple[str, int]], str]],
    ) -> None:
        """Create ordinary, non-unique indexes used for query performance."""
        for fields, name in indexes:
            self.ensure_index(fields, name=name, unique=False)

    def ensure_unique_index(
        self,
        fields: list[tuple[str, int]],
        *,
        name: str | None = None,
    ) -> None:
        self.ensure_index(fields, name=name, unique=True)

    def insert(self, document: dict[str, Any]) -> str:
        payload = _bson_safe(dict(document))
        payload.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        result = self._collection.insert_one(payload)
        return str(result.inserted_id)

    def find(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return list(self._collection.find(filters or {}, {"_id": 0}).limit(limit))

    def update(self, filters: dict[str, Any], update: dict[str, Any]) -> bool:
        result = self._collection.update_one(filters, _bson_safe(dict(update)))
        return result.matched_count > 0

    def delete_many(self, filters: dict[str, Any] | None = None) -> int:
        result = self._collection.delete_many(filters or {})
        return int(result.deleted_count)

    def ensure_unique_index(self, fields: list[tuple[str, int]], *, name: str | None = None) -> None:
        self._collection.create_index(fields, unique=True, name=name)

    def ensure_indexes_for(self, indexes: list[tuple[list[tuple[str, int]], str]]) -> None:
        for fields, name in indexes:
            self._collection.create_index(fields, name=name)

    def close(self) -> None:
        self._client.close()
