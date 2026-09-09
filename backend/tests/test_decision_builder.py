from app.api.schemas import DecisionRule
from app.decision.rule_builder import RuleBuilder
from app.engine.decision_engine import DecisionEngine


def test_compile_emits_engine_contract():
    result = RuleBuilder().compile({
        "id": "par30-alert",
        "name": "PAR30 alert",
        "conditions": [{"field": "par30", "operator": "gt", "value": 0.08}],
        "actions": [{"type": "alert", "parameters": {"severity": "high"}}],
    })

    assert result["valid"] is True
    assert result["compiled_rule"]["contract"] == "decision-engine-v1"
    assert DecisionRule.model_validate(result["compiled_rule"]).id == "par30-alert"


def test_compiled_rule_triggers_engine():
    compiled = RuleBuilder().compile({
        "id": "par30-alert",
        "name": "PAR30 alert",
        "conditions": [{"field": "par30", "operator": "gt", "value": 0.08}],
        "actions": [{"type": "alert"}],
    })
    rule = DecisionRule.model_validate(compiled["compiled_rule"])
    result = DecisionEngine().evaluate({"par30": 0.09}, [rule])

    assert result["triggered_rules"] == ["par30-alert"]
    assert result["actions"][0]["type"] == "alert"
