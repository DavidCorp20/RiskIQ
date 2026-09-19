from app.decision.decision_recommendations import DecisionRecommendationEngine


def test_high_ews_requires_human_approval():
    engine = DecisionRecommendationEngine()
    result = engine.recommend(
        dataset_id="dataset-1",
        ews_summary={
            "available": True,
            "as_of": "2026-09-19",
            "methodology": "portfolio-ews-v1",
            "top_alerts": [{
                "loan_id": "L1",
                "score": 82,
                "band": "critical",
                "signals": [{"code": "DPD_SEVERITY"}],
                "features": {"current_balance": 10000},
            }],
        },
    )
    assert len(result) == 1
    assert result[0]["action"] == "preventive_block"
    assert result[0]["action_level"] == "high"
    assert result[0]["requires_human_approval"] is True
    assert result[0]["customer_action_executed"] is False


def test_medium_ews_requires_human_approval():
    engine = DecisionRecommendationEngine()
    result = engine.recommend(
        dataset_id="dataset-1",
        ews_summary={
            "available": True,
            "top_alerts": [{
                "loan_id": "L2",
                "score": 60,
                "band": "high",
                "signals": [{"code": "DPD_DETERIORATION"}],
                "features": {"current_balance": 5000},
            }],
        },
    )
    assert result[0]["action"] == "limit_reduction"
    assert result[0]["requires_human_approval"] is True


def test_low_ews_is_review_only():
    engine = DecisionRecommendationEngine()
    result = engine.recommend(
        dataset_id="dataset-1",
        ews_summary={
            "available": True,
            "top_alerts": [{
                "loan_id": "L3",
                "score": 30,
                "band": "watch",
                "signals": [{"code": "EXPOSURE_MATERIAL"}],
                "features": {"current_balance": 1000},
            }],
        },
    )
    assert result[0]["action"] == "review"
    assert result[0]["action_level"] == "low"
    assert result[0]["requires_human_approval"] is False
