from app.decision.decision_intelligence import DecisionIntelligenceService


def test_high_par30_recommends_origination_review():
    result = DecisionIntelligenceService().build(
        {"facts": {"par30": {"value": 0.10}, "par90": {"value": 0.001}}, "alerts": ["PAR30_HIGH"]},
        [],
    )
    assert result["status"] == "high"
    assert result["recommendations"][0]["code"] == "REVIEW_ORIGINATION_RISK"
    assert result["decision_policy"] == "suggested"


def test_high_par90_prioritizes_collections():
    result = DecisionIntelligenceService().build(
        {"facts": {"par30": {"value": 0.02}, "par90": {"value": 0.01}}, "alerts": ["PAR90_CRITICAL"]},
        [],
    )
    assert result["status"] == "critical"
    assert any(r["code"] == "PRIORITIZE_COLLECTIONS" for r in result["recommendations"])
