from __future__ import annotations

from datetime import date
from typing import Any

from app.analytics.snapshot_engine import SnapshotEngine
from app.data.persistence import PortfolioPersistenceService
from app.decision.workspace import DecisionWorkspaceService


class DatasetIntelligenceService:
    """Build one coherent, real-data intelligence response for a persisted dataset."""

    CONTRACT_VERSION = "dataset-intelligence-v1"

    def __init__(self) -> None:
        self.persistence = PortfolioPersistenceService()
        self.snapshot_engine = SnapshotEngine()
        self.workspace = DecisionWorkspaceService()

    def run(
        self,
        dataset_id: str,
        snapshot_date: str | None = None,
        custom_rules: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        datasets = self.persistence.datasets.find({"dataset_id": dataset_id}, limit=1)
        if not datasets:
            raise KeyError("Dataset not found")

        records = self.persistence.portfolio_records.find(
            {"dataset_id": dataset_id}, limit=100000
        )
        portfolio = self._portfolio(dataset_id)
        loans = portfolio["loans"]
        installments = portfolio["installments"]

        as_of = snapshot_date or date.today().isoformat()
        current_snapshot = self.snapshot_engine.build(
            loans=loans,
            installments=installments,
            snapshot_date=as_of,
            business_id=dataset_id,
        )

        analysis = self._analysis(records)
        previous = self._previous_snapshot(dataset_id, current_snapshot["snapshot_date"])
        previous_for_workspace = previous or self._empty_previous(current_snapshot)

        workspace = self.workspace.run(
            {
                "current": current_snapshot,
                "previous": previous_for_workspace,
                "current_analysis": analysis,
                "custom_rules": custom_rules or [],
            }
        )

        snapshot_id = self.persistence.snapshots.insert(
            {**current_snapshot, "dataset_id": dataset_id}
        )

        return {
            "status": workspace["status"],
            "contract_version": self.CONTRACT_VERSION,
            "dataset": datasets[0],
            "dataset_id": dataset_id,
            "snapshot": {"id": snapshot_id, **current_snapshot},
            "previous_snapshot": previous,
            "analysis": analysis,
            "workspace": workspace,
            "governance": {
                "real_dataset": True,
                "analytics_are_deterministic": True,
                "customer_actions_executed": False,
                "trend_available": previous is not None,
            },
        }

    def _portfolio(self, dataset_id: str) -> dict[str, list[dict[str, Any]]]:
        return {
            "customers": self.persistence.customers.find({"dataset_id": dataset_id}, limit=100000),
            "loans": self.persistence.loans.find({"dataset_id": dataset_id}, limit=100000),
            "installments": self.persistence.installments.find({"dataset_id": dataset_id}, limit=100000),
            "payments": self.persistence.payments.find({"dataset_id": dataset_id}, limit=100000),
        }

    @staticmethod
    def _analysis(records: list[dict[str, Any]]) -> dict[str, Any]:
        from app.analytics.portfolio_intelligence import PortfolioIntelligenceService

        return PortfolioIntelligenceService().analyze(records)

    def _previous_snapshot(self, dataset_id: str, current_date: str) -> dict[str, Any] | None:
        rows = self.persistence.snapshots.find({"dataset_id": dataset_id}, limit=500)
        candidates = [
            row for row in rows
            if str(row.get("snapshot_date") or "") < current_date
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda row: str(row.get("snapshot_date") or ""))

    @staticmethod
    def _empty_previous(current: dict[str, Any]) -> dict[str, Any]:
        return {
            "snapshot_date": current.get("snapshot_date"),
            "business_id": current.get("business_id"),
            "active_loans": 0,
            "outstanding_balance": 0,
            "par7": 0,
            "par30": 0,
            "par60": 0,
            "par90": 0,
        }
