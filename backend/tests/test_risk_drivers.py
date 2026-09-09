from app.analytics.risk_drivers import RiskDriverEngine


def test_driver_ranks_segment_by_excess_risk_and_exposure():
    analysis = {
        "portfolio": {"par30": 0.08},
        "segments": [
            {"segment": "A", "par30": 0.20, "share_of_portfolio": 0.30, "balance": 30000, "loans": 120},
            {"segment": "B", "par30": 0.10, "share_of_portfolio": 0.10, "balance": 10000, "loans": 20},
            {"segment": "C", "par30": 0.04, "share_of_portfolio": 0.40, "balance": 40000, "loans": 150},
        ],
    }
    result = RiskDriverEngine().build(analysis)
    assert result[0]["key"] == "A"
    assert result[0]["causality"] == "associative"
    assert result[0]["confidence"] == "high"
