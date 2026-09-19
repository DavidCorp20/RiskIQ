from __future__ import annotations

from typing import Any


def _pct(value: float) -> float:
    return round(value * 100, 2)


class RiskFactsService:
    """Builds deterministic, explainable facts from portfolio metrics."""

    def build(self, metrics: dict[str, Any]) -> dict[str, Any]:
        par30 = float(metrics.get("par30", 0) or 0)
        par60 = float(metrics.get("par60", 0) or 0)
        par90 = float(metrics.get("par90", 0) or 0)
        active_loans = int(metrics.get("active_loans", 0) or 0)
        outstanding = float(metrics.get("outstanding_balance", 0) or 0)

        facts: list[dict[str, Any]] = []
        alerts: list[dict[str, Any]] = []

        facts.append({"id": "portfolio_size", "label": "Exposición activa", "value": outstanding, "unit": "currency", "severity": "info"})
        facts.append({"id": "active_loans", "label": "Créditos activos", "value": active_loans, "unit": "count", "severity": "info"})
        facts.append({"id": "par30", "label": "PAR30", "value": _pct(par30), "unit": "percent", "severity": "critical" if par30 >= 0.08 else "warning" if par30 >= 0.05 else "normal"})
        facts.append({"id": "par60", "label": "PAR60", "value": _pct(par60), "unit": "percent", "severity": "critical" if par60 >= 0.04 else "warning" if par60 >= 0.02 else "normal"})
        facts.append({"id": "par90", "label": "PAR90", "value": _pct(par90), "unit": "percent", "severity": "critical" if par90 >= 0.005 else "warning" if par90 >= 0.0025 else "normal"})

        if par30 >= 0.08:
            alerts.append({"code": "PAR30_HIGH", "severity": "high", "title": "Mora PAR30 elevada", "fact": "par30", "threshold": 8, "message": "PAR30 supera el umbral de 8%. Revisar originación, segmentos y gestión de cobranza."})
        if par90 >= 0.005:
            alerts.append({"code": "PAR90_CRITICAL", "severity": "critical", "title": "PAR90 crítico", "fact": "par90", "threshold": 0.5, "message": "PAR90 supera el 0.5%. Priorizar diagnóstico de deterioro y recuperación."})
        if par60 > par30 and par30 > 0:
            alerts.append({"code": "METRIC_INCONSISTENCY", "severity": "warning", "title": "Revisar consistencia PAR", "fact": "par60", "message": "PAR60 no debería superar PAR30. Verificar datos o definición de métricas."})

        return {"facts": facts, "alerts": alerts, "summary": self._summary(par30, par90, alerts)}

    @staticmethod
    def _summary(par30: float, par90: float, alerts: list[dict[str, Any]]) -> dict[str, Any]:
        if any(a["severity"] == "critical" for a in alerts):
            status = "critical"
            text = "La cartera presenta señales críticas que requieren investigación inmediata."
        elif alerts:
            status = "warning"
            text = "La cartera presenta señales de riesgo que requieren revisión."
        elif par30 > 0:
            status = "watch"
            text = "La cartera presenta mora; conviene monitorear su evolución."
        else:
            status = "healthy"
            text = "No se detectan alertas de riesgo en las reglas básicas."
        return {"status": status, "text": text, "alert_count": len(alerts)}
