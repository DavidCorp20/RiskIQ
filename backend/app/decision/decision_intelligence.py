from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DecisionRecommendation:
    code: str
    title: str
    priority: str
    rationale: str
    evidence: dict[str, Any]
    mode: str = "suggested"

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "title": self.title,
            "priority": self.priority,
            "rationale": self.rationale,
            "evidence": self.evidence,
            "mode": self.mode,
        }


class DecisionIntelligenceService:
    """Turns measured risk facts/drivers into reviewable recommendations.

    This layer recommends actions; it never executes customer actions automatically.
    """

    def build(self, risk_facts: dict[str, Any], drivers: list[dict[str, Any]]) -> dict[str, Any]:
        recommendations: list[DecisionRecommendation] = []
        alerts = risk_facts.get("alerts", [])

        par30 = self._number(risk_facts.get("facts", {}).get("par30", {}).get("value"))
        par90 = self._number(risk_facts.get("facts", {}).get("par90", {}).get("value"))

        if par30 >= 0.08:
            recommendations.append(DecisionRecommendation(
                code="REVIEW_ORIGINATION_RISK",
                title="Revisar originación y criterios de admisión",
                priority="high",
                rationale="PAR30 supera el umbral configurado; conviene revisar si el deterioro está relacionado con originación, segmentos o producto.",
                evidence={"par30": par30, "alert_count": len(alerts)},
            ))
        if par90 >= 0.005:
            recommendations.append(DecisionRecommendation(
                code="PRIORITIZE_COLLECTIONS",
                title="Priorizar cobranza sobre exposición 90+",
                priority="critical",
                rationale="PAR90 supera el umbral configurado y requiere priorización de recuperación.",
                evidence={"par90": par90},
            ))
        if drivers:
            top = drivers[0]
            recommendations.append(DecisionRecommendation(
                code="INVESTIGATE_TOP_DRIVER",
                title=f"Investigar driver {top.get('key')}",
                priority=top.get("severity", "watch"),
                rationale="Existe una asociación observada entre mayor mora y exposición material; investigar antes de aplicar una acción permanente.",
                evidence=top.get("evidence", {}),
            ))

        status = "critical" if any(r.priority == "critical" for r in recommendations) else "high" if recommendations else "healthy"
        return {
            "status": status,
            "recommendations": [r.to_dict() for r in recommendations],
            "decision_policy": "suggested",
            "principles": [
                "Las recomendaciones se basan en evidencia calculada.",
                "La asociación no implica causalidad.",
                "Las acciones requieren revisión humana en el MVP.",
            ],
        }

    @staticmethod
    def _number(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0
