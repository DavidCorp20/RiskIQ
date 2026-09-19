from app.api.schemas import DecisionRule, RuleAction, RuleCondition
from app.engine.decision_engine import DecisionEngine
from app.analytics.decision_engine import DecisionEngineService


def test_rule_triggers_when_all_conditions_match() -> None:
    rule = DecisionRule(
        id="par30-high",
        name="High PAR30",
        conditions=[RuleCondition(field="par30", operator="gt", value=0.08)],
        actions=[RuleAction(type="create_alert", parameters={"severity": "high"})],
    )

    result = DecisionEngine().evaluate({"par30": 0.10}, [rule])

    assert result["triggered_rules"] == ["par30-high"]
    assert result["actions"][0]["type"] == "create_alert"


def test_rule_does_not_trigger_when_condition_fails() -> None:
    rule = DecisionRule(
        id="par30-high",
        name="High PAR30",
        conditions=[RuleCondition(field="par30", operator="gt", value=0.08)],
    )

    result = DecisionEngine().evaluate({"par30": 0.05}, [rule])

    assert result["triggered_rules"] == []
    assert result["actions"] == []


def _risk(par30=0.0, par60=0.0, par90=0.0, exposure=1000):
    return {"available": True, "exposure": exposure, "par": {
        "par30": {"ratio": par30}, "par60": {"ratio": par60}, "par90": {"ratio": par90}
    }}


def test_risk_decision_engine_prioritizes_critical_and_requires_human_review() -> None:
    result = DecisionEngineService().build(_risk(par30=0.10, par90=0.02))
    first = result["decisions"][0]
    assert first["id"] == "par90_review"
    assert first["severity"] == "critical"
    assert first["requires_human_review"] is True
    assert first["executed"] is False
    assert result["cards"][0]["recommended_action"]


def test_risk_decision_engine_detects_bucket_inconsistency() -> None:
    result = DecisionEngineService().build(_risk(par30=0.10, par60=0.20))
    item = next(x for x in result["decisions"] if x["id"] == "bucket_inconsistency")
    assert item["severity"] == "critical"


def test_risk_decision_engine_translates_npl_proxy() -> None:
    result = DecisionEngineService().build(_risk(), {"available": True, "ratio": 0.06, "definition": "NPL90_proxy"})
    item = next(x for x in result["decisions"] if x["id"] == "npl_review")
    assert item["severity"] == "high"
    assert "regulatory_definition=false" in item["evidence"]


def test_risk_decision_engine_has_monitoring_card_when_healthy() -> None:
    result = DecisionEngineService().build(_risk())
    assert result["decisions"][0]["id"] == "portfolio_monitor"
    assert result["decisions"][0]["severity"] == "low"
    assert result["governance"]["customer_actions_executed"] is False
