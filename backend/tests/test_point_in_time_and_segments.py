from app.analytics.risk_analytics import RiskAnalyticsService
from app.data.portfolio_projection import PortfolioProjectionService


def test_point_in_time_analytics_uses_latest_snapshot_once_per_loan():
    rows = [
        {"loan_id":"L1","snapshot_date":"2026-01-31","outstanding_principal":100,"dpd":0},
        {"loan_id":"L2","snapshot_date":"2026-01-31","outstanding_principal":100,"dpd":30},
        {"loan_id":"L1","snapshot_date":"2026-02-28","outstanding_principal":90,"dpd":30},
        {"loan_id":"L2","snapshot_date":"2026-02-28","outstanding_principal":80,"dpd":0},
    ]
    result = RiskAnalyticsService().analyze(rows)
    assert result["loan_count"] == 2
    assert result["exposure"] == 170
    assert result["par"]["par30"]["balance"] == 90
    assert result["par"]["par30"]["ratio"] == 0.5294


def test_point_in_time_analytics_supports_undated_baseline_without_double_counting():
    rows = [
        {"loan_id":"L1","outstanding_principal":100,"dpd":0},
        {"loan_id":"L1","outstanding_principal":90,"dpd":30},
        {"loan_id":"L2","outstanding_principal":50,"dpd":0},
    ]
    result = RiskAnalyticsService().analyze(rows)
    assert result["loan_count"] == 2
    assert result["exposure"] == 140
    assert result["par"]["par30"]["balance"] == 90


def test_projection_rebuild_keeps_loans_missing_from_new_month():
    history = [
        {"loan_id":"L1","customer_id":"C1","snapshot_date":"2026-01-31","outstanding_principal":100},
        {"loan_id":"L2","customer_id":"C2","snapshot_date":"2026-01-31","outstanding_principal":200},
        {"loan_id":"L1","customer_id":"C1","snapshot_date":"2026-02-28","outstanding_principal":80},
    ]
    projection = PortfolioProjectionService().project(history)
    loans = {row["loan_id"]: row for row in projection["loans"]}
    assert set(loans) == {"L1", "L2"}
    assert loans["L1"]["outstanding_principal"] == 80
    assert loans["L2"]["outstanding_principal"] == 200
    assert projection["summary"]["loan_count"] == 2


def test_projection_prefers_latest_snapshot_for_each_loan():
    rows = [
        {"loan_id":"L1","customer_id":"C1","snapshot_date":"2026-01-31","outstanding_principal":100},
        {"loan_id":"L1","customer_id":"C1","snapshot_date":"2026-03-31","outstanding_principal":60},
        {"loan_id":"L1","customer_id":"C1","snapshot_date":"2026-02-28","outstanding_principal":80},
    ]
    loans = PortfolioProjectionService().project(rows)["loans"]
    assert len(loans) == 1
    assert loans[0]["outstanding_principal"] == 60
    assert loans[0]["snapshot_date"] == "2026-03-31"
