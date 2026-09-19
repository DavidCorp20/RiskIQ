from __future__ import annotations

from typing import Any


class NPLAnalyticsService:
    """Transparent NPL proxy using 90+ DPD outstanding balance.

    This is an analytical proxy, not a regulatory NPL definition.
    """

    def analyze(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        total = 0.0
        npl = 0.0
        loans = 0
        npl_loans = 0
        for row in rows:
            balance = self._number(row.get("outstanding_principal"))
            if balance <= 0:
                continue
            loans += 1
            total += balance
            if self._number(row.get("dpd")) >= 90:
                npl += balance
                npl_loans += 1
        return {
            "definition": "NPL90_proxy",
            "label": "NPL proxy (90+ DPD)",
            "balance": round(npl, 2),
            "ratio": round(npl / total, 4) if total else 0,
            "affected_loans": npl_loans,
            "loans_with_exposure": loans,
            "available": loans > 0 and any("dpd" in r for r in rows),
            "regulatory_definition": False,
        }

    @staticmethod
    def _number(value: Any) -> float:
        try:
            return max(float(value or 0), 0.0)
        except (TypeError, ValueError):
            return 0.0
