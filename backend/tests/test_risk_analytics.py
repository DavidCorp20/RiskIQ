from app.analytics.risk_analytics import RiskAnalyticsService


def test_risk_analytics_uses_outstanding_exposure_and_dpd_buckets():
    rows = [
        {"outstanding_principal": 100, "dpd": 0, "segment": "A", "product_id": "P1", "origination_date": "2026-01-10"},
        {"outstanding_principal": 200, "dpd": 10, "segment": "A", "product_id": "P1", "origination_date": "2026-01-10"},
        {"outstanding_principal": 300, "dpd": 35, "segment": "B", "product_id": "P2", "origination_date": "2026-02-10"},
        {"outstanding_principal": 400, "dpd": 95, "segment": "B", "product_id": "P2", "origination_date": "2026-02-10"},
    ]

    result = RiskAnalyticsService().analyze(rows)

    assert result["loan_count"] == 4
    assert result["exposure"] == 1000
    assert result["par"]["par7"]["ratio"] == 0.9
    assert result["par"]["par30"]["ratio"] == 0.7
    assert result["par"]["par60"]["ratio"] == 0.4
    assert result["par"]["par90"]["ratio"] == 0.4
    assert result["methodology"]["deterministic"] is True
    assert result["methodology"]["causality_inferred"] is False


def test_risk_analytics_returns_zero_ratios_for_zero_exposure():
    result = RiskAnalyticsService().analyze([
        {"outstanding_principal": 0, "dpd": 120, "segment": "A"},
        {"outstanding_principal": 0, "dpd": 0, "segment": "B"},
    ])

    assert result["available"] is False
    assert result["loan_count"] == 0
    assert result["exposure"] == 0
    assert all(bucket["ratio"] == 0 for bucket in result["par"].values())


def test_risk_analytics_flags_evidence_backed_concentration_driver():
    rows = [
        {"outstanding_principal": 900, "dpd": 40, "segment": "HighRisk", "product_id": "P1"},
        {"outstanding_principal": 100, "dpd": 0, "segment": "Other", "product_id": "P2"},
    ]

    result = RiskAnalyticsService().analyze(rows)

    assert result["drivers"]
    assert result["drivers"][0]["id"] == "segment:HighRisk"
    assert result["drivers"][0]["confidence"] == "deterministic"
    assert result["drivers"][0]["exposure_share"] == 0.9
