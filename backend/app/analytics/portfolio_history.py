from __future__ import annotations

from typing import Any


class PortfolioHistoryService:
    """Compare point-in-time snapshots without inventing a trend."""

    METRICS = ("outstanding_balance", "active_loans", "par7", "par30", "par60", "par90")

    def compare(self, current: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
        if not self._is_comparable(current, previous):
            return self._baseline(current)

        assert previous is not None
        changes: dict[str, dict[str, float | None]] = {}
        for metric in self.METRICS:
            current_value = self._number(current.get(metric))
            previous_value = self._number(previous.get(metric))
            delta = self._round(current_value - previous_value)
            pct_change = None if previous_value == 0 else self._round(delta / abs(previous_value))
            changes[metric] = {"current": current_value, "previous": previous_value, "delta": delta, "pct_change": pct_change}

        par30_delta = changes["par30"]["delta"] or 0.0
        par90_delta = changes["par90"]["delta"] or 0.0
        balance_delta = changes["outstanding_balance"]["delta"] or 0.0
        loan_delta = changes["active_loans"]["delta"] or 0.0

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

        drivers = []
        if par90_delta > 0:
            drivers.append({"metric": "PAR90", "delta": par90_delta, "direction": "up", "severity": "critical" if par90_delta >= 0.005 else "high"})
        if par30_delta > 0:
            drivers.append({"metric": "PAR30", "delta": par30_delta, "direction": "up", "severity": "high" if par30_delta >= 0.01 else "medium"})
        if balance_delta != 0:
            drivers.append({"metric": "outstanding_balance", "delta": balance_delta, "direction": "up" if balance_delta > 0 else "down", "severity": "context"})
        if loan_delta != 0:
            drivers.append({"metric": "active_loans", "delta": loan_delta, "direction": "up" if loan_delta > 0 else "down", "severity": "context"})

        return {
            "current_snapshot_date": current.get("snapshot_date"),
            "previous_snapshot_date": previous.get("snapshot_date"),
            "trend_available": True,
            "status": status,
            "changes": changes,
            "alerts": alerts,
            "drivers": drivers,
            "summary": self._summary(status, par30_delta, par90_delta),
            "interpretation": self._interpretation(status, par30_delta, par90_delta, balance_delta),
            "governance": {"causality_inferred": False, "requires_human_review": True, "customer_actions_executed": False},
            "causality": "not_inferred",
        }

    @staticmethod
    def _is_comparable(current: dict[str, Any], previous: dict[str, Any] | None) -> bool:
        if not previous:
            return False
        current_date = current.get("snapshot_date")
        previous_date = previous.get("snapshot_date")
        if current_date and previous_date and str(current_date) == str(previous_date):
            return False
        return True

    @staticmethod
    def _baseline(current: dict[str, Any]) -> dict[str, Any]:
        return {
            "current_snapshot_date": current.get("snapshot_date"),
            "previous_snapshot_date": None,
            "trend_available": False,
            "status": "baseline",
            "changes": {},
            "alerts": [],
            "drivers": [],
            "summary": "Primer corte registrado: no hay histórico comparable para evaluar tendencia.",
            "interpretation": "La lectura refleja el estado actual de la cartera. Los cambios de mora requieren un corte anterior comparable.",
            "governance": {"causality_inferred": False, "requires_human_review": True, "customer_actions_executed": False},
            "causality": "not_inferred",
        }

    @staticmethod
    def _round(value: float) -> float:
        return round(value, 10)

    @staticmethod
    def _summary(status: str, par30_delta: float, par90_delta: float) -> str:
        if status == "deteriorating":
            return f"Deterioro observado: PAR30 {par30_delta:+.2%} y PAR90 {par90_delta:+.2%} vs. snapshot previo."
        if status == "improving":
            return f"Mejora observada: PAR30 {par30_delta:+.2%} y PAR90 {par90_delta:+.2%} vs. snapshot previo."
        return "Cartera estable en los indicadores de mora comparados."

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
