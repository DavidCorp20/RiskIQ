from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.data.mongo import MongoRepository
from app.data.reconciliation import merge_enriched, snapshot_key


class PortfolioPersistenceService:
    """Persistence adapter for landing data, mappings and canonical projections."""

    def __init__(self) -> None:
        self.customers = MongoRepository("customers")
        self.loans = MongoRepository("loans")
        self.installments = MongoRepository("installments")
        self.payments = MongoRepository("payments")
        self.snapshots = MongoRepository("portfolio_snapshots")
        self.portfolio_records = MongoRepository("portfolio_records")
        self.datasets = MongoRepository("datasets")
        self.dataset_mappings = MongoRepository("dataset_mappings")

    def save_batch(self, collection: str, rows: list[dict[str, Any]]) -> int:
        repository = getattr(self, collection, None)
        if repository is None:
            raise ValueError(f"Unsupported portfolio collection: {collection}")
        for row in rows:
            repository.insert(row)
        return len(rows)

    def save_normalized_portfolio(
        self,
        rows: list[dict[str, Any]],
        dataset_id: str,
        source_name: str,
        quality_result: dict[str, Any] | None = None,
    ) -> int:
        documents = [{**row, "dataset_id": dataset_id, "source_name": source_name} for row in rows]
        for document in documents:
            self.portfolio_records.insert(document)
        return len(documents)

    def reconcile_update(self, existing: dict[str, Any], incoming: dict[str, Any], dataset_id: str, source_name: str, force: bool = False) -> dict[str, Any]:
        """Update one logical historical observation without creating a duplicate key."""
        merged = dict(incoming) if force else merge_enriched(existing, incoming)
        merged["dataset_id"] = dataset_id
        merged["source_name"] = source_name
        merged["reconciled_at"] = datetime.now(timezone.utc).isoformat()
        self.portfolio_records.update(
            {"dataset_id": dataset_id, "loan_id": existing.get("loan_id"), "snapshot_date": existing.get("snapshot_date")},
            {"$set": merged},
        )
        return merged

    def save_dataset_mapping(self, dataset_id: str, mappings: list[dict[str, Any]], source_name: str | None = None) -> str:
        return self.dataset_mappings.insert({
            "dataset_id": dataset_id,
            "source_name": source_name,
            "mappings": mappings,
            "mapped_fields": len(mappings),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

    def get_dataset_mapping(self, dataset_id: str) -> dict[str, Any] | None:
        rows = self.dataset_mappings.find({"dataset_id": dataset_id})
        return max(rows, key=lambda item: str(item.get("updated_at") or "")) if rows else None

    def save_dataset_metadata(
        self,
        dataset_id: str,
        source_name: str,
        source_rows: int,
        quality_result: dict[str, Any],
        projection_summary: dict[str, Any],
    ) -> str:
        """Create a portfolio once and refresh its metadata on subsequent snapshots."""
        document = {
            "dataset_id": dataset_id,
            "source_name": source_name,
            "row_count": source_rows,
            "quality_score": quality_result.get("quality_score"),
            "quality_status": quality_result.get("status"),
            "quality_issue_count": quality_result.get("issue_count", 0),
            "quality_issues": quality_result.get("issues", []),
            "projection_summary": projection_summary,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        existing = self.datasets.find({"dataset_id": dataset_id}, limit=1)
        if existing:
            self.datasets.update({"dataset_id": dataset_id}, {"$set": document})
            return str(existing[0].get("dataset_id") or dataset_id)
        document["created_at"] = datetime.now(timezone.utc).isoformat()
        return self.datasets.insert(document)

    def save_projection(self, portfolio: dict[str, Any], dataset_id: str, business_id: str | None = None) -> dict[str, int]:
        """Replace the current canonical projection for this dataset.

        Historical source rows live in portfolio_records; canonical collections
        are point-in-time working tables and therefore must not accumulate a copy
        of every monthly snapshot.
        """
        repositories = (self.customers, self.loans, self.installments, self.payments)
        for repository in repositories:
            repository.delete_many({"dataset_id": dataset_id})
        return {
            "customers": self._save_projection_collection(self.customers, portfolio.get("customers", []), dataset_id, business_id),
            "loans": self._save_projection_collection(self.loans, portfolio.get("loans", []), dataset_id, business_id),
            "installments": self._save_projection_collection(self.installments, portfolio.get("installments", []), dataset_id, business_id),
            "payments": self._save_projection_collection(self.payments, portfolio.get("payments", []), dataset_id, business_id),
        }

    @staticmethod
    def _save_projection_collection(repository: MongoRepository, rows: list[dict[str, Any]], dataset_id: str, business_id: str | None) -> int:
        for row in rows:
            document = {**row, "dataset_id": dataset_id}
            if business_id is not None:
                document["business_id"] = business_id
            repository.insert(document)
        return len(rows)

    def health(self) -> dict[str, bool]:
        repositories = {
            "customers": self.customers,
            "loans": self.loans,
            "installments": self.installments,
            "payments": self.payments,
            "snapshots": self.snapshots,
            "portfolio_records": self.portfolio_records,
            "datasets": self.datasets,
            "dataset_mappings": self.dataset_mappings,
        }
        result = {}
        for name, repository in repositories.items():
            try:
                result[name] = repository.ping()
            except Exception:
                result[name] = False
        return result
