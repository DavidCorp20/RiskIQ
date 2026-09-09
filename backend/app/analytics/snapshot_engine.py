from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.analytics.portfolio_metrics import portfolio_health


class SnapshotEngine:
    """Create deterministic point-in-time portfolio snapshots from canonical rows."""

    def build(
        self,
        loans: list[dict[str, Any]],
        installments: list[dict[str, Any]],
        snapshot_date: str | date | datetime,
        business_id: str | None = None,
    ) -> dict[str, Any]:
        as_of = self._date(snapshot_date)
        loan_objects = [self._loan(row) for row in loans]
        installment_objects = [self._installment(row) for row in installments]
        metrics = portfolio_health(loan_objects, installment_objects, as_of)

        return {
            "snapshot_date": as_of.isoformat(),
            "business_id": business_id,
            "active_loans": metrics["active_loans"],
            "outstanding_balance": metrics["outstanding_balance"],
            "par7": metrics["par7"],
            "par30": metrics["par30"],
            "par60": metrics["par60"],
            "par90": metrics["par90"],
            "metric_basis": "balance-weighted outstanding principal",
        }

    @staticmethod
    def _date(value: str | date | datetime) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value))

    @staticmethod
    def _loan(row: dict[str, Any]):
        from app.domain.models import Loan

        return Loan(
            loan_id=str(row.get("loan_id")),
            customer_id=str(row.get("customer_id")),
            business_id=str(row.get("business_id") or ""),
            product_id=str(row.get("product_id") or ""),
            origination_date=SnapshotEngine._date(row["origination_date"])
            if row.get("origination_date")
            else date.min,
            principal=float(row.get("principal") or 0),
            outstanding_principal=float(row.get("outstanding_principal") or 0),
            status=str(row.get("status") or "active"),
        )

    @staticmethod
    def _installment(row: dict[str, Any]):
        from app.domain.models import Installment

        return Installment(
            installment_id=str(row.get("installment_id")),
            loan_id=str(row.get("loan_id")),
            due_date=SnapshotEngine._date(row["due_date"])
            if row.get("due_date")
            else date.min,
            scheduled_amount=float(row.get("scheduled_amount") or 0),
            paid_amount=float(row.get("paid_amount") or 0),
        )
