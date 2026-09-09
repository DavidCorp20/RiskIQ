from app.decision.decision_center import DecisionCenterService


def test_decision_center_prioritizes_critical_cards():
    service = DecisionCenterService()
    result = service.build({
        "status": "critical",
        "cards": {"items": [
            {"id": "high-1", "priority": "high", "title": "High"},
            {"id": "critical-1", "priority": "critical", "title": "Critical"},
        ]},
        "drivers": [{"key": "segment-a", "impact_score": 0.2}],
        "history": {"status": "deteriorating"},
    }, [{"status": "proposed"}, {"status": "resolved"}])

    assert result["status"] == "critical"
    assert result["counts"]["critical"] == 1
    assert result["counts"]["resolved_history"] == 1
    assert result["priority_cards"][0]["priority"] == "critical"
    assert result["governance"]["decision_mode"] == "human_review"
