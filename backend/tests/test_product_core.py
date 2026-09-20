from app.api.schemas import DecisionRule, RuleAction, RuleCondition
from app.domain.core_contracts import RiskRunContract
from app.domain.core_pipeline import RiskCorePipeline
ROWS=[{"loan_id":"L1","snapshot_date":"2026-09-01","dpd":0,"outstanding_principal":1000},{"loan_id":"L2","snapshot_date":"2026-09-01","dpd":35,"outstanding_principal":2000},{"loan_id":"L3","snapshot_date":"2026-09-01","dpd":95,"outstanding_principal":3000}]
def test_core_contract_and_flow():
    r=RiskCorePipeline().run(ROWS,dataset_id="ds-1",snapshot_id="s-1")
    assert isinstance(r,RiskRunContract); assert r.contract_version=="risk-core-v1"; assert r.exposure==6000; assert r.audit.event_type=="risk_core_run"; assert {x.name for x in r.metrics}>={"exposure","par30","par60","par90"}
def test_core_decision_uses_analytics_facts():
    rule=DecisionRule(id="par90-review",name="PAR90 review",conditions=[RuleCondition(field="par90",operator="gte",value=0.4)],actions=[RuleAction(type="decision",parameters={"outcome":"REVIEW"})])
    r=RiskCorePipeline().run(ROWS,[rule]); assert r.decision and r.decision.decision=="REVIEW"; assert r.decision.triggered_rules==["par90-review"]
