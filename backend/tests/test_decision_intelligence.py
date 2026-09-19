from app.decision.decision_intelligence import DecisionIntelligenceService


def test_high_par30_recommends_origination_review():
    result = DecisionIntelligenceService().build(
        {
            "facts": [
                {"id": "par30", "value": 10.0},
                {"id": "par90", "value": 0.001},
            ],
            "alerts": ["PAR30_HIGH"],
        },
        [],
    )
    assert result["status"] == "high"
    assert result["recommendations"][0]["code"] == "REVIEW_ORIGINATION_RISK"
    assert result["decision_policy"] == "suggested"


def test_high_par90_prioritizes_collections():
    result = DecisionIntelligenceService().build(
        {
            "facts": [
                {"id": "par30", "value": 2.0},
                {"id": "par90", "value": 1.0},
            ],
            "alerts": ["PAR90_CRITICAL"],
        },
        [],
    )
    assert result["status"] == "critical"
    assert any(r["code"] == "PRIORITIZE_COLLECTIONS" for r in result["recommendations"])
