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
        return {"code":self.code,"title":self.title,"priority":self.priority,"rationale":self.rationale,"evidence":self.evidence,"mode":self.mode}

class DecisionIntelligenceService:
    """Turns measured risk facts/drivers into reviewable recommendations."""

    def build(self, risk_facts: dict[str, Any], drivers: list[dict[str, Any]]) -> dict[str, Any]:
        recommendations: list[DecisionRecommendation] = []
        alerts = risk_facts.get("alerts", [])
        facts = {str(item.get("id")): item for item in risk_facts.get("facts", []) if isinstance(item, dict)}
        par30 = self._number(facts.get("par30", {}).get("value")) / 100
        par90 = self._number(facts.get("par90", {}).get("value")) / 100

        if par30 >= 0.08:
            recommendations.append(DecisionRecommendation("REVIEW_ORIGINATION_RISK","Revisar originación y criterios de admisión","high","PAR30 supera el umbral configurado; conviene revisar si el deterioro está relacionado con originación, segmentos o producto.",{"par30":par30,"alert_count":len(alerts)}))
        if par90 >= 0.005:
            recommendations.append(DecisionRecommendation("PRIORITIZE_COLLECTIONS","Priorizar cobranza sobre exposición 90+","critical","PAR90 supera el umbral configurado y requiere priorización de recuperación.",{"par90":par90}))
        if drivers:
            top = drivers[0]
            recommendations.append(DecisionRecommendation("INVESTIGATE_TOP_DRIVER",f"Investigar driver {top.get('key')}",top.get("severity","watch"),"Existe una asociación observada entre mayor mora y exposición material; investigar antes de aplicar una acción permanente.",top.get("evidence",{})))

        status = "critical" if any(r.priority == "critical" for r in recommendations) else "high" if recommendations else "healthy"
        return {"status":status,"recommendations":[r.to_dict() for r in recommendations],"decision_policy":"suggested","principles":["Las recomendaciones se basan en evidencia calculada.","La asociación no implica causalidad.","Las acciones requieren revisión humana en el MVP."]}

    @staticmethod
    def _number(value: Any) -> float:
        try: return float(value or 0)
        except (TypeError, ValueError): return 0.0
