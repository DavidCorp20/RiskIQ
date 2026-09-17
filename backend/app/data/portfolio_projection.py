from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any


class PortfolioProjectionService:
    """Build the point-in-time canonical portfolio from normalized source rows.

    Source rows remain the immutable longitudinal landing layer. The canonical
    loan projection represents the latest observation per loan, preventing old
    monthly states from becoming duplicate active loans in current analytics.
    """

    def project(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        latest_rows: dict[str, dict[str, Any]] = {}
        anonymous: list[dict[str, Any]] = []
        for row in rows:
            loan_id = self._text(row.get("loan_id"))
            if not loan_id:
                anonymous.append(row)
                continue
            current = latest_rows.get(loan_id)
            if current is None or self._snapshot_key(row) >= self._snapshot_key(current):
                latest_rows[loan_id] = row

        projection_rows = list(latest_rows.values()) + anonymous
        customers: dict[str, dict[str, Any]] = {}
        loans: dict[str, dict[str, Any]] = {}
        installments: list[dict[str, Any]] = []
        payments: list[dict[str, Any]] = []

        installment_counter = 0
        for row in projection_rows:
            customer_id = self._text(row.get("customer_id"))
            loan_id = self._text(row.get("loan_id"))
            if not customer_id or not loan_id:
                continue
            customers.setdefault(customer_id, {"customer_id": customer_id, "segment": self._text(row.get("segment")) or None})
            loans[loan_id] = {
                "loan_id": loan_id,
                "customer_id": customer_id,
                "product_id": self._text(row.get("product_id")) or None,
                "origination_date": self._date(row.get("origination_date")),
                "snapshot_date": self._snapshot_key(row) or None,
                "principal": self._decimal(row.get("principal", row.get("scheduled_amount"))),
                "outstanding_principal": self._decimal(row.get("outstanding_principal")),
                "status": self._text(row.get("status")) or "active",
                "segment": self._text(row.get("segment")) or None,
            }
            if row.get("due_date") is not None or row.get("scheduled_amount") is not None:
                installment_counter += 1
                installments.append({"installment_id": f"{loan_id}-inst-{installment_counter}", "loan_id": loan_id, "due_date": self._date(row.get("due_date")), "scheduled_amount": self._decimal(row.get("scheduled_amount")), "paid_amount": self._decimal(row.get("paid_amount")), "snapshot_date": self._snapshot_key(row) or None})
            if row.get("payment_date") is not None and row.get("paid_amount") is not None:
                payments.append({"payment_id": f"{loan_id}-payment-{len(payments) + 1}", "loan_id": loan_id, "payment_date": self._date(row.get("payment_date")), "amount": self._decimal(row.get("paid_amount")), "snapshot_date": self._snapshot_key(row) or None})

        return {"customers": list(customers.values()), "loans": list(loans.values()), "installments": installments, "payments": payments, "summary": {"customer_count": len(customers), "loan_count": len(loans), "installment_count": len(installments), "payment_count": len(payments), "snapshot_date": max((self._snapshot_key(r) for r in projection_rows if self._snapshot_key(r)), default=None)}}

    @staticmethod
    def _snapshot_key(row: dict[str, Any]) -> str:
        for field in ("snapshot_date", "snapshot_month", "as_of_date"):
            value = row.get(field)
            if value not in (None, ""):
                return str(value)[:10]
        return ""

    @staticmethod
    def _text(value: Any) -> str:
        return str(value).strip() if value not in (None, "") else ""

    @staticmethod
    def _decimal(value: Any) -> Decimal:
        if value in (None, ""): return Decimal("0")
        try: return Decimal(str(value))
        except (InvalidOperation, ValueError): return Decimal("0")

    @staticmethod
    def _date(value: Any) -> str | None:
        if value in (None, ""): return None
        if isinstance(value, datetime): return value.date().isoformat()
        if isinstance(value, date): return value.isoformat()
        text = str(value).strip()
        try: return datetime.fromisoformat(text).date().isoformat()
        except ValueError:
            try: return date.fromisoformat(text).isoformat()
            except ValueError: return None
