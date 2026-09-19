from app.analytics.portfolio_history import PortfolioHistoryService


def test_history_detects_par30_deterioration():
    service = PortfolioHistoryService()
    result = service.compare(
        {"snapshot_date": "2026-09-08", "outstanding_balance": 110000, "active_loans": 120, "par30": 0.09, "par90": 0.02},
        {"snapshot_date": "2026-09-01", "outstanding_balance": 100000, "active_loans": 110, "par30": 0.07, "par90": 0.02},
    )
    assert result["status"] == "deteriorating"
    assert result["changes"]["par30"]["delta"] == 0.02
    assert result["alerts"][0]["code"] == "PAR30_DETERIORATION"


def test_history_detects_improvement():
    service = PortfolioHistoryService()
    result = service.compare(
        {"snapshot_date": "2026-09-08", "par30": 0.05, "par90": 0.01},
        {"snapshot_date": "2026-09-01", "par30": 0.07, "par90": 0.02},
    )
    assert result["status"] == "improving"
    assert result["alerts"] == []
