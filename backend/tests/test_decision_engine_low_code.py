from app.api.schemas import DecisionRule, RuleAction, RuleCondition
from app.engine.decision_engine import DecisionEngine


def test_or_logic_triggers_when_one_condition_matches():
    rule = DecisionRule(
        id="risk-or",
        name="Riesgo combinado",
        logic="OR",
        conditions=[
            RuleCondition(field="par30", operator="gt", value=0.08),
            RuleCondition(field="par90", operator="gt", value=0.03),
        ],
        actions=[RuleAction(type="review")],
    )
    result = DecisionEngine().evaluate({"par30": 0.04, "par90": 0.04}, [rule])
    assert result["triggered_rules"] == ["risk-or"]


def test_between_operator_is_evaluable_and_traceable():
    rule = DecisionRule(
        id="exposure-band",
        name="Banda de exposición",
        conditions=[RuleCondition(field="outstanding_balance", operator="between", value=[1000, 5000])],
        actions=[RuleAction(type="alert")],
    )
    result = DecisionEngine().evaluate({"outstanding_balance": 2500}, [rule])
    assert result["triggered_rules"] == ["exposure-band"]
    assert result["evaluation_trace"][0]["conditions"][0]["matched"] is True
