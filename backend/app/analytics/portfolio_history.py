from __future__ import annotations

from typing import Any


class PortfolioHistoryService:
    """Compare point-in-time snapshots without inferring causality."""

    METRICS = ("outstanding_balance", "active_loans", "par7", "par30", "par60", "par90")

    def compare(self, current: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
        changes: dict[str, dict[str, float | None]] = {}
        for metric in self.METRICS:
            current_value = self._number(current.get(metric))
            previous_value = self._number(previous.get(metric))
            delta = self._round(current_value - previous_value)
            pct_change = None if previous_value == 0 else self._round(delta / abs(previous_value))
            changes[metric] = {
                "current": current_value,
                "previous": previous_value,
                "delta": delta,
                "pct_change": pct_change,
            }

        par30_delta = changes["par30"]["delta"] or 0.0
        par90_delta = changes["par90"]["delta"] or 0.0
        balance_delta = changes["outstanding_balance"]["delta"] or 0.0

        alerts: list[dict[str, Any]] = []
        if par30_delta >= 0.01:
            alerts.append({"code": "PAR30_DETERIORATION", "severity": "high", "delta": par30_delta})
        if par90_delta >= 0.005:
            alerts.append({"code": "PAR90_DETERIORATION", "severity": "critical", "delta": par90_delta})

        if par90_delta > 0 or par30_delta > 0:
            status = "deteriorating"
        elif par90_delta < 0 or par30_delta < 0:
            status = "improving"
        else:
            status = "stable"

        return {
            "current_snapshot_date": current.get("snapshot_date"),
            "previous_snapshot_date": previous.get("snapshot_date"),
            "status": status,
            "changes": changes,
            "alerts": alerts,
            "interpretation": self._interpretation(status, par30_delta, par90_delta, balance_delta),
            "causality": "not_inferred",
        }

    @staticmethod
    def _round(value: float) -> float:
        return round(value, 10)

    @staticmethod
    def _interpretation(status: str, par30_delta: float, par90_delta: float, balance_delta: float) -> str:
        if status == "deteriorating":
            return "La mora observada aumentó entre snapshots; investigar segmentos, vintages y cobranza antes de atribuir causas."
        if status == "improving":
            return "La mora observada disminuyó entre snapshots; validar si la mejora se sostiene en períodos posteriores."
        return "No se observa un cambio de mora suficiente para clasificar la cartera como deteriorada o mejorada."

    @staticmethod
    def _number(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0
