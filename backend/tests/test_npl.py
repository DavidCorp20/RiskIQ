from app.analytics.npl import NPLAnalyticsService


def test_npl_proxy_90_plus_dpd():
    rows = [
        {"loan_id": "L1", "dpd": 10, "outstanding_principal": 1000},
        {"loan_id": "L2", "dpd": 95, "outstanding_principal": 2000},
        {"loan_id": "L3", "dpd": 0, "outstanding_principal": 1000},
    ]
    result = NPLAnalyticsService().analyze(rows)
    assert result["available"] is True
    assert result["balance"] == 2000.0
    assert result["ratio"] == 0.5
    assert result["affected_loans"] == 1
    assert result["regulatory_definition"] is False
