from app.analytics.risk_analytics import RiskAnalyticsService


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
