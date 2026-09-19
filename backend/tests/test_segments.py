from app.analytics.segment_analytics import SegmentAnalyticsService


def test_custom_segment_uses_latest_snapshot_per_loan() -> None:
    rows = [
        {
            "loan_id": "L1",
            "snapshot_date": "2026-01-31",
            "age": 29,
            "employment": "employed",
            "outstanding_principal": 100,
            "dpd": 0,
        },
        {
            "loan_id": "L1",
            "snapshot_date": "2026-02-28",
            "age": 30,
            "employment": "employed",
            "outstanding_principal": 90,
            "dpd": 35,
        },
        {
            "loan_id": "L2",
            "snapshot_date": "2026-02-28",
            "age": 42,
            "employment": "self_employed",
            "outstanding_principal": 110,
            "dpd": 10,
        },
    ]

    result = SegmentAnalyticsService.calculate(
        rows,
        [
            {"field": "age", "operator": ">=", "value": 30},
            {"field": "employment", "operator": "=", "value": "employed"},
        ],
    )

    assert result["loan_count"] == 1
    assert result["exposure"] == 90
    assert result["par30"] == 1.0


def test_custom_segment_supports_arbitrary_source_columns() -> None:
    rows = [
        {"loan_id": "L1", "snapshot_date": "2026-02-28", "vehicle_owner": True, "outstanding_principal": 100, "dpd": 0},
        {"loan_id": "L2", "snapshot_date": "2026-02-28", "vehicle_owner": False, "outstanding_principal": 200, "dpd": 45},
    ]

    result = SegmentAnalyticsService.calculate(
        rows,
        [{"field": "vehicle_owner", "operator": "=", "value": False}],
    )

    assert result["loan_count"] == 1
    assert result["exposure"] == 200
    assert result["par30"] == 1.0
