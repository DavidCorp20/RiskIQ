from app.api.schemas import DecisionRule, RuleAction, RuleCondition
from app.decision.decision_engine import DecisionEngine


def test_decision_engine_triggers_matching_rule():
    rule = DecisionRule(
        id="r1",
        name="Review PAR30",
        conditions=[RuleCondition(field="par30", operator="gt", value=0.08)],
        actions=[RuleAction(type="review")],
        mode="suggested",
    )
    result = DecisionEngine().evaluate({"par30": 0.10}, [rule])
    assert result["triggered_rules"] == ["r1"]
    assert result["actions"][0]["rule_id"] == "r1"
