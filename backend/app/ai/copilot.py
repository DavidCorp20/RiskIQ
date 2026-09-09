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
        return {
            "facts": risk_facts.get("facts", {}),
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
        top_driver = context["drivers"][0] if context["drivers"] else None

        evidence_lines = []
        for key in ("par30", "par60", "par90", "exposure"):
            fact = context["facts"].get(key)
            if fact:
                evidence_lines.append(f"{fact.get('label', key)}: {fact.get('value')}{fact.get('unit', '')}")

        if top_driver:
            explanation = (
                f"El principal driver observado es {top_driver.get('key')}, "
                "pero la evidencia disponible es asociativa y requiere investigación antes de concluir causalidad."
            )
        elif alerts:
            explanation = "La cartera presenta alertas calculadas que requieren revisión según la política configurada."
        else:
            explanation = "No se identificaron alertas con la evidencia suministrada."

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
