from __future__ import annotations
from hashlib import sha256
import json
from typing import Any

from app.analytics.risk_analytics import RiskAnalyticsService
from app.data.persistence import PortfolioPersistenceService
from app.market.service import MarketContextService
from app.predictive.transition_engine import TransitionEngine
from app.predictive.pd_engine import PDEngine
from app.predictive.survival_engine import SurvivalEngine
from app.risk_events.repository import RiskActionRepository,RiskEventRepository
from app.stress_testing.stress_engine import StressEngine

class RiskIntelligenceProvider:
    """Single server-side evidence contract for executive and Copilot consumers.

    The provider aggregates already-calculated deterministic evidence. It does not
    create new risk decisions and never allows the AI layer to mutate values.
    """
    def __init__(self):
        self.persistence=PortfolioPersistenceService()
        self.analytics=RiskAnalyticsService()
        self.market=MarketContextService()
        self.events=RiskEventRepository()
        self.actions=RiskActionRepository()
        self.transition=TransitionEngine()
        self.pd=PDEngine()
        self.survival=SurvivalEngine()
        self.stress=StressEngine()

    async def build(self,dataset_id:str)->dict[str,Any]:
        rows=self.persistence.portfolio_records.find({"dataset_id":dataset_id},limit=100000)
        if not rows: raise ValueError("Dataset has no portfolio records")
        risk=self.analytics.analyze(rows)
        market=await self.market.get_context()
        events=self.events.list(dataset_id=dataset_id,limit=500)
        actions=self.actions.list(limit=500)
        dataset_actions=[a for a in actions if any(e.get("event_id")==a.get("event_id") for e in events)]
        matrix=self.transition.build_matrix(rows)
        ratings=self.pd.ratings(matrix,1)
        survival_rows=[r for r in rows if r.get("duration") is not None]
        survival=self.survival.kaplan_meier(survival_rows) if survival_rows else {"points":[],"methodology":"kaplan-meier-v1","sample_size":0}
        payload={
            "contract_version":"risk-intelligence-v1",
            "dataset_id":dataset_id,
            "deterministic":True,
            "ai_mutable_fields":[],
            "portfolio":{"analytics":risk,"npl":self._npl(risk)},
            "market":market,
            "risk_events":{"events":events,"actions":dataset_actions},
            "predictive":{"transition_matrix":matrix.model_dump(),"pd_ratings":[x.model_dump() for x in ratings],"survival":survival.model_dump() if hasattr(survival,"model_dump") else survival},
            "stress_testing":{"available":True,"baseline":self._baseline(risk),"scenarios":["BASE","ADVERSE","SEVERE_STRESS"],"projection_requires_validated_sensitivities":True},
        }
        payload["evidence_hash"]=sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
        return payload

    @staticmethod
    def _baseline(risk):
        par=risk.get("par") or {}
        return {"par30":float((par.get("par30") or {}).get("ratio",0)),"par60":float((par.get("par60") or {}).get("ratio",0)),"par90":float((par.get("par90") or {}).get("ratio",0)),"exposure":float(risk.get("exposure",0))}
    @staticmethod
    def _npl(risk):
        return risk.get("npl") or None
