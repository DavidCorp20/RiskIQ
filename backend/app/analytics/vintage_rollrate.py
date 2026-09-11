from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any


class VintageRollRateService:
    """Deterministic vintage and delinquency analytics without inventing history."""

    BUCKETS = (
        (0, 0, "current"),
        (1, 7, "1_7"),
        (8, 30, "8_30"),
        (31, 60, "31_60"),
        (61, 90, "61_90"),
        (91, 10**9, "90_plus"),
    )

    def analyze(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        warnings: list[str] = []
        valid = [r for r in rows if self._balance(r) > 0]
        if not valid:
            return {
                "vintages": [],
                "buckets": [],
                "roll_rates": [],
                "roll_rate_available": False,
                "history_dates": [],
                "warnings": ["No hay exposición válida para calcular vintage o roll rate."],
            }

        if not any(self._date(r.get("origination_date")) for r in valid):
            warnings.append("No hay fechas de originación suficientes para calcular vintage.")
        if not any(self._has_dpd(r) for r in valid):
            warnings.append("No hay DPD disponible; no se puede construir distribución de mora ni roll rate.")

        history_dates = sorted({self._date(r.get("snapshot_date")) for r in valid if self._date(r.get("snapshot_date"))})
        vintages = self._vintages(valid)
        buckets = self._buckets(valid)
        roll_rates = self._roll_rates(valid, history_dates)
        roll_rate_available = bool(roll_rates)

        if len(history_dates) < 2:
            warnings.append("Roll rate requiere al menos dos snapshots comparables de la misma cartera.")
        elif not roll_rates:
            warnings.append("Hay fechas históricas, pero no existe DPD comparable por préstamo para calcular migraciones.")

        return {
            "vintages": vintages,
            "buckets": buckets,
            "roll_rates": roll_rates,
            "roll_rate_available": roll_rate_available,
            "history_dates": [d.isoformat() for d in history_dates],
            "warnings": warnings,
        }

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
            result.append({
                "vintage": month,
                "loans": len(items),
                "balance": round(balance, 2),
                "par30": round(par30, 4),
                "par90": round(par90, 4),
            })
        return result

    def _buckets(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        total = sum(self._balance(r) for r in rows)
        result = []
        for low, high, name in self.BUCKETS:
            balance = sum(self._balance(r) for r in rows if low <= self._dpd(r) <= high)
            result.append({"bucket": name, "balance": round(balance, 2), "share": round(balance / total, 4) if total else 0})
        return result

    def _roll_rates(self, rows: list[dict[str, Any]], history_dates: list[date]) -> list[dict[str, Any]]:
        if len(history_dates) < 2:
            return []
        # A roll rate is only valid when the same loan has DPD observations on
        # consecutive snapshots. Source rows may represent a flattened history;
        # loan_id is therefore required to establish identity.
        observations: dict[str, dict[date, dict[str, Any]]] = defaultdict(dict)
        for row in rows:
            loan_id = str(row.get("loan_id") or row.get("id") or "").strip()
            snapshot = self._date(row.get("snapshot_date"))
            if not loan_id or not snapshot or not self._has_dpd(row):
                continue
            observations[loan_id][snapshot] = row

        if not observations:
            return []

        output: list[dict[str, Any]] = []
        for previous_date, current_date in zip(history_dates, history_dates[1:]):
            transitions: dict[str, dict[str, float]] = defaultdict(lambda: {"loans": 0, "balance": 0.0})
            for loan_id, by_date in observations.items():
                previous = by_date.get(previous_date)
                current = by_date.get(current_date)
                if not previous or not current:
                    continue
                source = self._bucket_name(self._dpd(previous))
                target = self._bucket_name(self._dpd(current))
                key = f"{source}->{target}"
                transitions[key]["loans"] += 1
                transitions[key]["balance"] += self._balance(previous)

            denominator: dict[str, float] = defaultdict(float)
            for key, value in transitions.items():
                source = key.split("->", 1)[0]
                denominator[source] += value["balance"]

            for key, value in sorted(transitions.items()):
                source, target = key.split("->", 1)
                denom = denominator[source]
                output.append({
                    "from": source,
                    "to": target,
                    "previous_snapshot_date": previous_date.isoformat(),
                    "current_snapshot_date": current_date.isoformat(),
                    "loans": int(value["loans"]),
                    "exposure": round(value["balance"], 2),
                    "rate": round(value["balance"] / denom, 4) if denom else 0,
                })
        return output

    def _bucket_name(self, dpd: int) -> str:
        for low, high, name in self.BUCKETS:
            if low <= dpd <= high:
                return name
        return "90_plus"

    @staticmethod
    def _has_dpd(row: dict[str, Any]) -> bool:
        return row.get("dpd") not in (None, "")

    @staticmethod
    def _balance(row: dict[str, Any]) -> float:
        try:
            return max(float(row.get("outstanding_principal") or row.get("outstanding_balance") or 0), 0)
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
