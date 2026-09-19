from app.decision.rule_builder import RuleBuilder


def test_valid_visual_rule():
    result = RuleBuilder().from_visual({
        "id": "par30-high",
        "name": "High PAR30",
        "conditions": [{"field": "par30", "operator": "gte", "value": 0.08}],
        "actions": [{"type": "alert", "parameters": {"severity": "high"}}],
    })
    assert result["valid"] is True
    assert result["normalized_rule"]["mode"] == "suggested"


def test_rejects_unsupported_operator_and_action():
    result = RuleBuilder().from_visual({
        "id": "bad-rule",
        "name": "Bad rule",
        "conditions": [{"field": "par30", "operator": "python", "value": 0.08}],
        "actions": [{"type": "execute_python"}],
    })
    assert result["valid"] is False
    assert len(result["errors"]) == 2
