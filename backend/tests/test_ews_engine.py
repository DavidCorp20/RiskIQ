from app.analytics.ews_engine import EWSEngine


def test_ews_detects_dpd_acceleration_and_bucket_migration():
    rows = [
        {"loan_id": "L1", "snapshot_date": "2026-01-01", "dpd": 5, "outstanding_principal": 1000},
        {"loan_id": "L1", "snapshot_date": "2026-02-01", "dpd": 20, "outstanding_principal": 980},
        {"loan_id": "L1", "snapshot_date": "2026-03-01", "dpd": 55, "outstanding_principal": 960},
    ]

    result = EWSEngine().calculate(rows)[0]

    assert result["loan_id"] == "L1"
    assert result["features"]["dpd_delta"] == 35
    assert result["features"]["dpd_acceleration"] == 20
    assert result["features"]["bucket_from"] == "early_1_29"
    assert result["features"]["bucket_to"] == "early_30_59"
    assert result["score"] > 25
    assert result["band"] in {"watch", "high", "critical"}


def test_ews_is_zero_for_stable_current_loan():
    rows = [
        {"loan_id": "L2", "snapshot_date": "2026-01-01", "dpd": 0, "outstanding_principal": 1000},
        {"loan_id": "L2", "snapshot_date": "2026-02-01", "dpd": 0, "outstanding_principal": 1000},
        {"loan_id": "L2", "snapshot_date": "2026-03-01", "dpd": 0, "outstanding_principal": 1000},
    ]

    result = EWSEngine().calculate(rows)[0]

    assert result["score"] == 5.0
    assert result["band"] == "normal"


def test_ews_keeps_loans_independent():
    rows = [
        {"loan_id": "A", "snapshot_date": "2026-01-01", "dpd": 0, "outstanding_principal": 100},
        {"loan_id": "A", "snapshot_date": "2026-02-01", "dpd": 10, "outstanding_principal": 90},
        {"loan_id": "B", "snapshot_date": "2026-01-01", "dpd": 90, "outstanding_principal": 500},
    ]

    results = EWSEngine().calculate(rows)

    assert [item["loan_id"] for item in results] == ["B", "A"]
    assert results[0]["band"] == "critical"
