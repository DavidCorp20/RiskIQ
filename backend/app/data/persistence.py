from __future__ import annotations

from typing import Any

from app.data.mongo import MongoRepository


class PortfolioPersistenceService:
    """Persists normalized portfolio records into separate Mongo collections."""

    def __init__(self) -> None:
        self.customers = MongoRepository("customers")
        self.loans = MongoRepository("loans")
        self.installments = MongoRepository("installments")
        self.payments = MongoRepository("payments")
        self.snapshots = MongoRepository("portfolio_snapshots")

    def save_batch(self, collection: str, rows: list[dict[str, Any]]) -> int:
        repository = getattr(self, collection, None)
        if repository is None:
            raise ValueError(f"Unsupported portfolio collection: {collection}")
        for row in rows:
            repository.insert(row)
        return len(rows)

    def health(self) -> dict[str, bool]:
        repositories = {
            "customers": self.customers,
            "loans": self.loans,
            "installments": self.installments,
            "payments": self.payments,
            "snapshots": self.snapshots,
        }
        result: dict[str, bool] = {}
        for name, repository in repositories.items():
            try:
                result[name] = repository.ping()
            except Exception:
                result[name] = False
        return result
