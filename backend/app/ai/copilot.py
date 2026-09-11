from __future__ import annotations

from typing import Any


class RiskCopilotService:
    """Provider-agnostic AI layer grounded in deterministic RiskIQ evidence."""

    def build_context(
        self,
        risk_facts: dict[str, Any],
        drivers: list[dict[str, Any]] | None = None,
        decisions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        raw_facts = risk_facts.get("facts", {})
        if isinstance(raw_facts, list):
            facts = {str(item.get("id")): item for item in raw_facts if isinstance(item, dict) and item.get("id")}
        elif isinstance(raw_facts, dict):
            facts = dict(raw_facts)
        else:
            facts = {}
        if "portfolio_size" in facts and "exposure" not in facts:
            facts["exposure"] = facts["portfolio_size"]
        return {
            "facts": facts,
            "alerts": risk_facts.get("alerts", []),
            "summary": risk_facts.get("summary", {}),
            "drivers": drivers or [],
            "decisions": decisions or [],
            "grounding_rules": [
                "Use only supplied calculated facts as facts.",
                "Clearly label hypotheses as hypotheses.",
                "Do not invent metrics, thresholds, causes, or outcomes.",
                "Causality must not be claimed from associative evidence.",
                "Recommendations remain reviewable by a human in the MVP.",
            ],
        }

    def answer(
        self,
        question: str,
        risk_facts: dict[str, Any],
        drivers: list[dict[str, Any]] | None = None,
        decisions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        context = self.build_context(risk_facts, drivers, decisions)
        summary = context["summary"]
        alerts = context["alerts"]
        facts = context["facts"]
        top_driver = context["drivers"][0] if context["drivers"] else None

        evidence_lines = []
        for key in ("par30", "par60", "par90", "exposure", "loan_count"):
            fact = facts.get(key)
            if fact:
                evidence_lines.append(f"{fact.get('label', key)}: {fact.get('value')}{fact.get('unit', '')}")

        priority = "Morosidad y concentración"
        evidence = ""
        impact = "La señal requiere priorización y revisión sobre la cartera expuesta."
        action = "Revisar la distribución por DPD, concentración y evolución histórica antes de modificar políticas."

        if top_driver:
            priority = top_driver.get("title") or top_driver.get("key") or priority
            evidence = top_driver.get("evidence", "Driver observado en la cartera.")
            share = top_driver.get("exposure_share")
            impact = (
                f"El driver concentra {share * 100:.1f}% de la exposición observada y presenta la señal de PAR30 indicada."
                if isinstance(share, (int, float))
                else "El driver representa una señal relevante de concentración o morosidad según la evidencia calculada."
            )
            action = "Desglosar este driver por DPD, región, empleo y vintage; validar causas y evaluar una acción de política antes de aplicarla."
            explanation = (
                f"Primero revisaría {priority}. La evidencia disponible indica: {evidence} "
                f"Impacto: {impact} Acción sugerida: {action} "
                "Es una señal descriptiva; requiere investigación antes de concluir causalidad."
            )
        elif alerts:
            priority = "Alertas calculadas"
            evidence = "Las alertas disponibles provienen de reglas determinísticas de RiskIQ."
            impact = "Indican situaciones que requieren revisión bajo la política vigente."
            action = "Validar cada alerta, cuantificar su exposición y decidir manualmente la acción correspondiente."
            explanation = f"Primero revisaría {priority}. {evidence} Impacto: {impact} Acción sugerida: {action}"
        elif facts:
            par30 = facts.get("par30")
            par90 = facts.get("par90")
            exposure = facts.get("exposure")
            loan_count = facts.get("loan_count")
            parts = []
            if par30:
                parts.append(f"PAR30 está en {par30.get('value')}{par30.get('unit', '')}")
            if par90:
                parts.append(f"PAR90 está en {par90.get('value')}{par90.get('unit', '')}")
            if exposure:
                parts.append(f"la exposición observada es {exposure.get('value')}{exposure.get('unit', '')}")
            if loan_count:
                parts.append(f"con {loan_count.get('value')} préstamos activos")
            evidence = "; ".join(parts)
            priority = "Morosidad de cartera"
            impact = "La morosidad observada debe contrastarse con concentración y tendencia para determinar dónde está la mayor exposición al riesgo."
            action = "Segmentar PAR30/PAR90 por producto, región, empleo y vintage; luego validar una acción de cobranza o política con revisión humana."
            explanation = f"Primero revisaría {priority}. Evidencia: {evidence}. Impacto: {impact} Acción sugerida: {action} No hay que interpretar la ausencia de una alerta como ausencia de riesgo."
        else:
            explanation = "No hay evidencia calculada suficiente para priorizar una revisión. Ejecuta el análisis del dataset y vuelve a consultar el Copilot."
            priority = "Evidencia insuficiente"
            evidence = explanation
            impact = "No evaluable con la información disponible."
            action = "Ejecutar el análisis del dataset antes de tomar una decisión."

        return {
            "question": question,
            "answer": explanation,
            "status": summary.get("status", "unknown"),
            "evidence": evidence_lines,
            "drivers": context["drivers"][:3],
            "decisions": context["decisions"][:3],
            "decision": {
                "priority": priority,
                "evidence": evidence,
                "impact": impact,
                "suggested_action": action,
                "human_review_required": True,
            },
            "grounded": True,
            "provider": "evidence_mode",
            "mode": "Evidence Mode",
            "note": "Respuesta determinística basada en evidencia calculada. Un proveedor LLM puede añadirse después sin cambiar el motor analítico.",
        }
