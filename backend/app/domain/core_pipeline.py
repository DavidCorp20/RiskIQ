from __future__ import annotations
from typing import Any
from app.analytics.risk_analytics import RiskAnalyticsService
from app.api.schemas import DecisionRule
from app.domain.core_contracts import AuditEventContract, DecisionContract, RiskFactContract, RiskMetricContract, RiskRunContract
from app.engine.decision_engine import DecisionEngine
class RiskCorePipeline:
    """Thin orchestration layer for the minimum RiskIQ product flow."""
    def __init__(self): self.analytics=RiskAnalyticsService(); self.decision_engine=DecisionEngine()
    def run(self, rows:list[dict[str,Any]], rules:list[DecisionRule]|None=None, *, dataset_id:str|None=None, snapshot_id:str|None=None, actor:str="system") -> RiskRunContract:
        if not rows: raise ValueError("rows must contain at least one portfolio observation")
        a=self.analytics.analyze(rows); par=a.get("par") or {}; as_of=a.get("snapshot")
        metrics=[RiskMetricContract(name="exposure",value=a.get("exposure"),unit="currency",as_of=as_of,methodology="sum active outstanding_principal"),RiskMetricContract(name="loan_count",value=a.get("loan_count"),unit="count",as_of=as_of,methodology="count active observations")]
        facts=[]
        for name in ("par30","par60","par90"):
            item=par.get(name) or {}; facts.append(RiskFactContract(code=name.upper(),value=item.get("ratio",0),evidence={"balance":item.get("balance"),"loans":item.get("loans"),"dpd_threshold":item.get("dpd_threshold")})); metrics.append(RiskMetricContract(name=name,value=item.get("ratio",0),unit="ratio",as_of=as_of,methodology=f"balance with dpd >= {name[3:]} / exposure")); metrics.append(RiskMetricContract(name=f"{name}_balance",value=item.get("balance",0),unit="currency",as_of=as_of,methodology=f"sum outstanding_principal where dpd >= {name[3:]}"))
        decision=None
        if rules:
            result=self.decision_engine.evaluate({"exposure":a.get("exposure",0),"loan_count":a.get("loan_count",0),"par30":(par.get("par30") or {}).get("ratio",0),"par60":(par.get("par60") or {}).get("ratio",0),"par90":(par.get("par90") or {}).get("ratio",0)},rules)
            decision=DecisionContract(status="executed" if result.get("triggered_rules") else "not_triggered",decision=result.get("decision") or result.get("outcome"),triggered_rules=result.get("triggered_rules",[]),reason_codes=result.get("reason_codes",[]),actions=result.get("actions",[]),evaluation_trace=result.get("evaluation_trace",[]))
        audit=AuditEventContract(event_type="risk_core_run",actor=actor,dataset_id=dataset_id,snapshot_id=snapshot_id,decision_id=decision.id if decision else None,evidence={"observations":len(rows),"exposure":a.get("exposure",0),"metrics":[m.name for m in metrics],"facts":[f.code for f in facts]})
        return RiskRunContract(dataset_id=dataset_id,snapshot_id=snapshot_id,observations=len(rows),exposure=float(a.get("exposure") or 0),metrics=metrics,facts=facts,decision=decision,audit=audit,methodology={"analytics":"RiskAnalyticsService","decisioning":"DecisionEngine","ai":"excluded from deterministic core","external_actions":False})
