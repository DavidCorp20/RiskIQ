from __future__ import annotations

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
    ) -> int:
        """Store normalized source rows without discarding source fields.

        Keeping the normalized landing records separately makes ingestion
        replayable and lets downstream domain projections evolve without
        re-uploading the original file.
        """
        documents = []
        for row in rows:
            documents.append(
                {
                    **row,
                    "dataset_id": dataset_id,
                    "source_name": source_name,
                }
            )
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
        }
        result: dict[str, bool] = {}
        for name, repository in repositories.items():
            try:
                result[name] = repository.ping()
            except Exception:
                result[name] = False
        return result
