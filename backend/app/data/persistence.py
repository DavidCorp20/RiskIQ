from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.data.mongo import MongoRepository


class PortfolioPersistenceService:
    """Persistence adapter for normalized portfolio data and audit-ready records."""

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
        """Store normalized source rows plus one audit-ready dataset metadata record."""
        quality_result = quality_result or {}
        self.datasets.insert(
            {
                "dataset_id": dataset_id,
                "source_name": source_name,
                "row_count": len(rows),
                "quality_score": quality_result.get("quality_score"),
                "quality_status": quality_result.get("status"),
                "quality_issue_count": quality_result.get("issue_count", 0),
                "quality_issues": quality_result.get("issues", []),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )

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
