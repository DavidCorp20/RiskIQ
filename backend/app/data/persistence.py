from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.data.mongo import MongoRepository


class PortfolioPersistenceService:
    """Persistence adapter for landing data and the canonical portfolio model."""

    def __init__(self) -> None:
        self.customers = MongoRepository("customers")
        self.loans = MongoRepository("loans")
        self.installments = MongoRepository("installments")
        self.payments = MongoRepository("payments")
        self.snapshots = MongoRepository("portfolio_snapshots")
        self.portfolio_records = MongoRepository("portfolio_records")
        self.datasets = MongoRepository("datasets")

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
        """Store normalized source rows with dataset lineage and quality metadata."""
        quality_result = quality_result or {}
        documents = [
            {
                **row,
                "dataset_id": dataset_id,
                "source_name": source_name,
            }
            for row in rows
        ]
        for document in documents:
            self.portfolio_records.insert(document)
        return len(documents)

    def save_dataset_metadata(
        self,
        dataset_id: str,
        source_name: str,
        source_rows: int,
        quality_result: dict[str, Any],
        projection_summary: dict[str, Any],
    ) -> str:
        """Persist one audit record describing the uploaded dataset and projection."""
        return self.datasets.insert(
            {
                "dataset_id": dataset_id,
                "source_name": source_name,
                "row_count": source_rows,
                "quality_score": quality_result.get("quality_score"),
                "quality_status": quality_result.get("status"),
                "quality_issue_count": quality_result.get("issue_count", 0),
                "quality_issues": quality_result.get("issues", []),
                "projection_summary": projection_summary,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    def save_projection(
        self,
        portfolio: dict[str, Any],
        dataset_id: str,
        business_id: str | None = None,
    ) -> dict[str, int]:
        """Persist the canonical customer/loan/installment/payment projection.

        Dataset lineage is retained on every projected document. This keeps the
        analytical model traceable back to the uploaded source dataset.
        """
        counts = {
            "customers": self._save_projection_collection(
                self.customers, portfolio.get("customers", []), dataset_id, business_id
            ),
            "loans": self._save_projection_collection(
                self.loans, portfolio.get("loans", []), dataset_id, business_id
            ),
            "installments": self._save_projection_collection(
                self.installments, portfolio.get("installments", []), dataset_id, business_id
            ),
            "payments": self._save_projection_collection(
                self.payments, portfolio.get("payments", []), dataset_id, business_id
            ),
        }
        return counts

    @staticmethod
    def _save_projection_collection(
        repository: MongoRepository,
        rows: list[dict[str, Any]],
        dataset_id: str,
        business_id: str | None,
    ) -> int:
        for row in rows:
            document = {
                **row,
                "dataset_id": dataset_id,
            }
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
        }
        result: dict[str, bool] = {}
        for name, repository in repositories.items():
            try:
                result[name] = repository.ping()
            except Exception:
                result[name] = False
        return result
