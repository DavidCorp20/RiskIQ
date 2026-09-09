from app.analytics.portfolio_intelligence import PortfolioIntelligenceService


def test_segment_becomes_risk_driver_when_par30_exceeds_portfolio():
    rows = [
        {"loan_id": "1", "segment": "A", "outstanding_principal": 7000, "dpd": 45},
        {"loan_id": "2", "segment": "A", "outstanding_principal": 3000, "dpd": 0},
        {"loan_id": "3", "segment": "B", "outstanding_principal": 10000, "dpd": 0},
    ]

    result = PortfolioIntelligenceService().analyze(rows)
    driver_segments = {driver["segment"] for driver in result["risk_drivers"] if driver["type"] == "segment_deterioration"}

    assert result["portfolio"]["par30"] == 0.35
    assert "A" in driver_segments


def test_material_segment_concentration_is_detected():
    rows = [
        {"loan_id": "1", "segment": "A", "outstanding_principal": 5000, "dpd": 0},
        {"loan_id": "2", "segment": "A", "outstanding_principal": 5000, "dpd": 0},
        {"loan_id": "3", "segment": "B", "outstanding_principal": 1000, "dpd": 0},
    ]

    result = PortfolioIntelligenceService().analyze(rows)
    assert any(d["type"] == "concentration" and d["segment"] == "A" for d in result["risk_drivers"])
