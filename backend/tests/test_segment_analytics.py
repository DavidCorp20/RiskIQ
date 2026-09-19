from app.analytics.segment_analytics import SegmentAnalyticsService


def test_segment_analytics_uses_latest_state_per_loan():
    rows = [
        {"loan_id":"L1","snapshot_date":"2026-01-31","outstanding_principal":100,"dpd":0,"age":31,"employment":"employed"},
        {"loan_id":"L1","snapshot_date":"2026-02-28","outstanding_principal":90,"dpd":45,"age":31,"employment":"employed"},
        {"loan_id":"L2","snapshot_date":"2026-02-28","outstanding_principal":50,"dpd":10,"age":25,"employment":"self"},
    ]
    result = SegmentAnalyticsService().calculate(rows, [{"field":"age","operator":">=","value":30}])
    assert result["loan_count"] == 1
    assert result["exposure"] == 90
    assert result["par30"] == 1.0


def test_segment_supports_boolean_like_custom_fields():
    rows = [
        {"loan_id":"L1","snapshot_date":"2026-02-28","outstanding_principal":100,"dpd":0,"vehicle_owner":False},
        {"loan_id":"L2","snapshot_date":"2026-02-28","outstanding_principal":200,"dpd":60,"vehicle_owner":True},
    ]
    result = SegmentAnalyticsService().calculate(rows, [{"field":"vehicle_owner","operator":"=","value":False}])
    assert result["loan_count"] == 1
    assert result["exposure"] == 100
    assert result["par30"] == 0
