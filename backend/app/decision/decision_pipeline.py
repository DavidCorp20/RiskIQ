from __future__ import annotations

from typing import Any

from app.analytics.portfolio_history import PortfolioHistoryService
from app.analytics.risk_drivers import RiskDriverEngine
from app.analytics.risk_facts import RiskFactsService
from app.api.schemas import DecisionRule
from app.decision.decision_cards import DecisionCardService
from app.decision.decision_intelligence import DecisionIntelligenceService
from app.engine.decision_engine import DecisionEngine


class DecisionPipelineService:
    """Orchestrate measured portfolio change into reviewable decision cards."""

    def __init__(self) -> None:
        self.history = PortfolioHistoryService()
        self.risk_facts = RiskFactsService()
        self.drivers = RiskDriverEngine()
        self.decisions = DecisionIntelligenceService()
        self.cards = DecisionCardService()
        self.engine = DecisionEngine()

    def build(self, current: dict[str, Any], previous: dict[str, Any], current_analysis: dict[str, Any] | None = None, custom_rules: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        history = self.history.compare(current, previous)
        metrics = {
            "active_loans": current.get("active_loans", 0),
            "outstanding_balance": current.get("outstanding_balance", 0),
            "par30": current.get("par30", 0),
            "par60": current.get("par60", 0),
            "par90": current.get("par90", 0),
        }
        risk_facts = self.risk_facts.build(metrics)
        analysis = current_analysis or {"portfolio": metrics, "segments": []}
        drivers = self.drivers.build(analysis)
        decisions = self.decisions.build(risk_facts, drivers)

        for alert in history["alerts"]:
            code = alert["code"]
            if code == "PAR30_DETERIORATION":
                decisions["recommendations"].append({"code":"INVESTIGATE_PAR30_TREND","title":"Investigar deterioro reciente de PAR30","priority":"high","rationale":"PAR30 aumentó frente al snapshot anterior; revisar vintage, segmentos y efectividad de cobranza.","evidence":{"current_par30":history["changes"]["par30"]["current"],"previous_par30":history["changes"]["par30"]["previous"],"delta":history["changes"]["par30"]["delta"]},"mode":"suggested"})
            elif code == "PAR90_DETERIORATION":
                decisions["recommendations"].append({"code":"ESCALATE_PAR90_TREND","title":"Escalar deterioro reciente de PAR90","priority":"critical","rationale":"PAR90 aumentó frente al snapshot anterior; priorizar análisis de recuperación y exposición afectada.","evidence":{"current_par90":history["changes"]["par90"]["current"],"previous_par90":history["changes"]["par90"]["previous"],"delta":history["changes"]["par90"]["delta"]},"mode":"suggested"})

        custom_result = {"triggered_rules": [], "actions": [], "evaluation_trace": []}
        if custom_rules:
            rules = [DecisionRule.model_validate(rule) for rule in custom_rules]
            custom_result = self.engine.evaluate(metrics, rules)
            for action in custom_result["actions"]:
                action_type = str(action.get("type", "review"))
                priority = "critical" if action_type == "block" else "high" if action_type in {"alert", "review"} else "watch"
                rule_id = str(action.get("rule_id", "custom-rule"))
                decisions["recommendations"].append({"code":f"CUSTOM_RULE_{rule_id.upper()}","title":self._action_title(action_type),"priority":priority,"rationale":"Regla institucional configurada por el usuario y activada por los hechos actuales.","evidence":{"rule_id":rule_id,"action_type":action_type,"facts":metrics},"mode":action.get("mode","suggested")})

        decisions["status"] = self._status(decisions["recommendations"])
        cards = self.cards.build(decisions["recommendations"])
        return {"status":decisions["status"],"history":history,"risk_facts":risk_facts,"drivers":drivers,"decisions":decisions,"custom_rules":custom_result,"cards":{"count":len(cards),"items":cards}}

    @staticmethod
    def _action_title(action_type: str) -> str:
        return {"alert":"Revisar alerta de regla institucional","recommend":"Evaluar recomendación de regla institucional","set_risk_level":"Revisar nivel de riesgo configurado","review":"Revisar decisión institucional","block":"Revisar bloqueo definido por regla"}.get(action_type,"Revisar regla institucional")

    @staticmethod
    def _status(recommendations: list[dict[str, Any]]) -> str:
        priorities = {str(item.get("priority", "watch")) for item in recommendations}
        if "critical" in priorities: return "critical"
        if "high" in priorities: return "high"
        return "healthy"
