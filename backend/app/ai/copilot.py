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

        if top_driver:
            explanation = (
                f"Primero revisaría {top_driver.get('title') or top_driver.get('key')}. "
                f"La evidencia disponible indica: {top_driver.get('evidence', 'driver observado en la cartera')}. "
                "Es una señal descriptiva; requiere investigación antes de concluir causalidad."
            )
        elif alerts:
            explanation = (
                "Primero revisaría las alertas calculadas y su impacto sobre la cartera. "
                "Las alertas son reglas/evidencia determinística y deben contrastarse con la política vigente."
            )
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
            explanation = (
                "Primero revisaría la morosidad y su evolución, empezando por PAR30 y PAR90. "
                + (f"En la evidencia actual, {evidence}. " if evidence else "La evidencia calculada está disponible, aunque faltan indicadores de morosidad para priorizar. ")
                + "No hay que interpretar la ausencia de una alerta calculada como ausencia de riesgo; conviene contrastar estos indicadores con segmentos, concentración y tendencia histórica."
            )
        else:
            explanation = "No hay evidencia calculada suficiente para priorizar una revisión. Ejecuta el análisis del dataset y vuelve a consultar el Copilot."

        return {
            "question": question,
            "answer": explanation,
            "status": summary.get("status", "unknown"),
            "evidence": evidence_lines,
            "drivers": context["drivers"][:3],
            "decisions": context["decisions"][:3],
            "grounded": True,
            "provider": "not_configured",
            "note": "Respuesta determinística de fallback. Con un proveedor LLM configurado, este contexto puede alimentar el Copilot sin cambiar el motor analítico.",
        }
