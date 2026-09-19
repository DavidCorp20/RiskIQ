from app.decision.decision_pipeline import DecisionPipelineService


def test_custom_rule_flows_into_decision_cards():
    result = DecisionPipelineService().build(
        current={"active_loans": 100, "outstanding_balance": 100000, "par30": 0.09, "par60": 0.04, "par90": 0.01},
        previous={"active_loans": 100, "outstanding_balance": 100000, "par30": 0.08, "par60": 0.04, "par90": 0.01},
        custom_rules=[{
            "id": "institution-par30",
            "name": "Institution PAR30 rule",
            "conditions": [{"field": "par30", "operator": "gt", "value": 0.08}],
            "actions": [{"type": "alert"}],
            "mode": "suggested",
            "enabled": True,
        }],
    )

    assert result["custom_rules"]["triggered_rules"] == ["institution-par30"]
    assert any(item["code"] == "CUSTOM_RULE_INSTITUTION-PAR30" for item in result["decisions"]["recommendations"])
