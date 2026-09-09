from app.api.schemas import DecisionRule, RuleAction, RuleCondition
from app.engine.decision_engine import DecisionEngine


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
