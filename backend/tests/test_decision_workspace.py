from app.decision.workspace import DecisionWorkspaceService


def test_workspace_runs_pipeline_and_center_with_custom_rule():
    service = DecisionWorkspaceService()
    result = service.run({
        "current": {
            "snapshot_date": "2026-09-08",
            "active_loans": 100,
            "outstanding_balance": 100000,
            "par30": 0.09,
            "par60": 0.04,
            "par90": 0.01,
        },
        "previous": {
            "snapshot_date": "2026-08-08",
            "active_loans": 100,
            "outstanding_balance": 95000,
            "par30": 0.07,
            "par60": 0.03,
            "par90": 0.005,
        },
        "custom_rules": [{
            "id": "par30-rule",
            "name": "Alerta PAR30",
            "conditions": [{"field": "par30", "operator": "gt", "value": 0.08}],
            "actions": [{"type": "alert", "parameters": {"message": "PAR30 alto"}}],
            "mode": "suggested",
            "enabled": True,
        }],
    })

    assert result["status"] == "critical"
    assert result["contract_version"] == "workspace-v1"
    assert result["rule_count"] == 1
    assert "par30-rule" in result["pipeline"]["custom_rules"]["triggered_rules"]
    assert result["decision_center"]["counts"]["total_cards"] >= 1
    assert result["governance"]["customer_actions_executed"] is False


def test_workspace_rejects_invalid_custom_rule_before_execution():
    service = DecisionWorkspaceService()
    result = service.run({
        "current": {"par30": 0.09},
        "previous": {"par30": 0.08},
        "custom_rules": [{
            "id": "bad-rule",
            "name": "Regla inválida",
            "conditions": [{"field": "par30", "operator": "python", "value": 0.08}],
            "actions": [{"type": "alert"}],
        }],
    })

    assert result["status"] == "invalid_rules"
    assert result["workspace"] is None
    assert result["rule_errors"]
