from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any


class VintageRollRateService:
    """Deterministic vintage and delinquency-bucket analytics from loan snapshots."""

    BUCKETS = ((0, 0, "current"), (1, 7, "1_7"), (8, 30, "8_30"), (31, 60, "31_60"), (61, 90, "61_90"), (91, 10**9, "90_plus"))

    def analyze(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        warnings: list[str] = []
        valid = [r for r in rows if self._balance(r) > 0]
        if not valid:
            return {"vintages": [], "buckets": [], "roll_rates": [], "roll_rate_available": False, "warnings": ["No hay exposición válida para calcular vintage o roll rate."]}

        if not any(self._date(r.get("origination_date")) for r in valid):
            warnings.append("No hay fechas de originación suficientes para calcular vintage.")
        if not any("dpd" in r and r.get("dpd") not in (None, "") for r in valid):
            warnings.append("No hay DPD disponible; no se puede construir distribución de mora ni roll rate.")

        vintages = self._vintages(valid)
        buckets = self._buckets(valid)
        roll_rate_available = self._has_history(valid)
        if not roll_rate_available:
            warnings.append("Roll rate requiere snapshots históricos de la misma cartera; no se infiere con una sola fotografía.")
        return {"vintages": vintages, "buckets": buckets, "roll_rates": [], "roll_rate_available": roll_rate_available, "warnings": warnings}

    def _vintages(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            d = self._date(row.get("origination_date"))
            if d:
                groups[d.strftime("%Y-%m")].append(row)
        result = []
        for month, items in sorted(groups.items()):
            balance = sum(self._balance(r) for r in items)
            par30 = sum(self._balance(r) for r in items if self._dpd(r) >= 30) / balance if balance else 0
            par90 = sum(self._balance(r) for r in items if self._dpd(r) >= 90) / balance if balance else 0
            result.append({"vintage": month, "loans": len(items), "balance": balance, "par30": round(par30, 4), "par90": round(par90, 4)})
        return result

    def _buckets(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        total = sum(self._balance(r) for r in rows)
        result = []
        for low, high, name in self.BUCKETS:
            balance = sum(self._balance(r) for r in rows if low <= self._dpd(r) <= high)
            result.append({"bucket": name, "balance": balance, "share": round(balance / total, 4) if total else 0})
        return result

    @staticmethod
    def _has_history(rows: list[dict[str, Any]]) -> bool:
        return any(r.get("snapshot_date") not in (None, "") for r in rows)

    @staticmethod
    def _balance(row: dict[str, Any]) -> float:
        try:
            return max(float(row.get("outstanding_principal") or 0), 0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _dpd(row: dict[str, Any]) -> int:
        try:
            return max(int(float(row.get("dpd") or 0)), 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _date(value: Any) -> date | None:
        if isinstance(value, date):
            return value
        if value in (None, ""):
            return None
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None
