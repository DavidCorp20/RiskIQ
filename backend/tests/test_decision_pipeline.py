from app.decision.decision_pipeline import DecisionPipelineService


def test_pipeline_creates_actionable_card_from_par30_trend():
    result = DecisionPipelineService().build(
        current={
            "snapshot_date": "2026-09-08",
            "active_loans": 120,
            "outstanding_balance": 110000,
            "par30": 0.09,
            "par60": 0.04,
            "par90": 0.01,
        },
        previous={
            "snapshot_date": "2026-09-01",
            "active_loans": 110,
            "outstanding_balance": 100000,
            "par30": 0.07,
            "par60": 0.04,
            "par90": 0.01,
        },
    )

    codes = {item["code"] for item in result["decisions"]["recommendations"]}
    assert "INVESTIGATE_PAR30_TREND" in codes
    assert result["cards"]["count"] >= 1
    assert result["history"]["status"] == "deteriorating"
