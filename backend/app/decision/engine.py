from __future__ import annotations

from typing import Any


class DecisionEngineService:
    """Deterministic risk-to-decision layer. It recommends; humans execute."""

    def run(self, risk: dict[str, Any], npl: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
        signals: list[dict[str, Any]] = []
        cards: list[dict[str, Any]] = []
        par = risk.get("par") or {}

        def ratio(bucket: str) -> float:
            return float((par.get(bucket) or {}).get("ratio") or 0)

        def add(signal_id: str, severity: str, title: str, reason: str, evidence: dict[str, Any], action: str) -> None:
            priority = {"critical": 1, "high": 2, "medium": 3, "low": 4}[severity]
            signal = {"id": signal_id, "severity": severity, "priority": priority, "title": title, "reason": reason, "evidence": evidence}
            signals.append(signal)
            cards.append({
                "id": f"decision:{signal_id}", "priority": priority, "severity": severity,
                "title": title, "rationale": reason, "evidence": evidence,
                "recommended_action": action, "requires_human_review": True, "executed": False,
            })

        p30, p90 = ratio("par30"), ratio("par90")
        if p90 >= 0.005:
            add("par90_critical", "critical", "Priorizar exposición 90+ DPD",
                "La exposición con 90 o más días de mora supera el umbral crítico definido por RiskIQ.",
                {"par90_ratio": p90, "threshold": 0.005}, "Revisar cuentas afectadas y priorizar gestión de recuperación.")
        if p30 >= 0.08:
            add("par30_high", "high", "Revisar deterioro PAR30",
                "El PAR30 supera el umbral de alerta alta definido por RiskIQ.",
                {"par30_ratio": p30, "threshold": 0.08}, "Segmentar la mora y revisar estrategias de cobranza y originación.")
        elif p30 >= 0.05:
            add("par30_watch", "medium", "Monitorear PAR30",
                "El PAR30 se encuentra en una zona de vigilancia definida por RiskIQ.",
                {"par30_ratio": p30, "threshold": 0.05}, "Monitorear evolución y revisar concentración por segmento.")

        for driver in (risk.get("drivers") or [])[:3]:
            share = float(driver.get("exposure_share") or 0)
            if share >= 0.50:
                did = str(driver.get("id") or "concentration")
                add(f"concentration:{did}", "high", "Concentración de riesgo relevante",
                    "Una dimensión concentra al menos la mitad de la exposición analizada.",
                    {"driver": driver, "threshold": 0.50}, "Revisar límites, concentración y desempeño del segmento identificado.")

        npl_value = float(npl.get("npl_ratio") or npl.get("ratio") or 0)
        if npl_value >= 0.005:
            add("npl90_proxy", "high", "Revisar NPL 90+ proxy",
                "La exposición 90+ DPD utilizada como proxy de NPL requiere revisión de cartera.",
                {"npl_ratio": npl_value, "definition": npl.get("definition", "NPL90_proxy"), "regulatory_definition": False},
                "Validar la definición regulatoria aplicable y revisar la exposición 90+ DPD.")

        cards.sort(key=lambda item: (item["priority"], item["id"]))
        signals.sort(key=lambda item: (item["priority"], item["id"]))
        status = "critical" if any(s["severity"] == "critical" for s in signals) else "high" if signals else "healthy"
        return {
            "status": status,
            "signals": signals,
            "cards": cards,
            "methodology": {"deterministic": True, "source": "risk_analytics+npl+analysis", "causality_inferred": False},
            "governance": {"requires_human_review": True, "customer_actions_executed": False, "ai_is_not_source_of_truth": True},
        }
