from app.analytics.risk_analytics import RiskAnalyticsService
from app.analytics.segment_analytics import SegmentAnalyticsService
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


def test_custom_segment_uses_latest_state_per_loan():
    rows = [
        {"loan_id":"L1","snapshot_date":"2026-01-31","outstanding_principal":100,"dpd":0,"age":29},
        {"loan_id":"L1","snapshot_date":"2026-02-28","outstanding_principal":90,"dpd":30,"age":30},
        {"loan_id":"L2","snapshot_date":"2026-02-28","outstanding_principal":60,"dpd":0,"age":40},
    ]
    result = SegmentAnalyticsService().calculate(rows, [{"field":"age","operator":">=","value":30}])
    assert result["loan_count"] == 2
    assert result["exposure"] == 150
    assert result["par30"] == 0.6
    assert result["par90"] == 0


def test_custom_segment_supports_multiple_conditions():
    rows = [
        {"loan_id":"L1","snapshot_date":"2026-02-28","outstanding_principal":100,"dpd":30,"employment":"employed"},
        {"loan_id":"L2","snapshot_date":"2026-02-28","outstanding_principal":50,"dpd":0,"employment":"self-employed"},
    ]
    result = SegmentAnalyticsService().calculate(rows, [
        {"field":"employment","operator":"=","value":"employed"},
        {"field":"dpd","operator":">=","value":30},
    ])
    assert result["loan_count"] == 1
    assert result["exposure"] == 100
    assert result["par30"] == 1.0


def test_custom_segment_contains_and_empty_operators():
    rows = [
        {"loan_id":"L1","snapshot_date":"2026-02-28","outstanding_principal":100,"employer":"Acme Bank"},
        {"loan_id":"L2","snapshot_date":"2026-02-28","outstanding_principal":50,"employer":""},
    ]
    contains = SegmentAnalyticsService().calculate(rows, [{"field":"employer","operator":"contains","value":"bank"}])
    empty = SegmentAnalyticsService().calculate(rows, [{"field":"employer","operator":"is_empty","value":None}])
    assert contains["loan_count"] == 1
    assert empty["loan_count"] == 1
