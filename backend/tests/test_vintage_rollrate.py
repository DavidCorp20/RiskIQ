from datetime import date

from app.analytics.vintage_rollrate import VintageRollRateService


def test_vintage_groups_by_origination_month():
    rows = [
        {"loan_id": "1", "origination_date": date(2026, 1, 15), "outstanding_principal": 1000, "dpd": 45},
        {"loan_id": "2", "origination_date": date(2026, 1, 20), "outstanding_principal": 3000, "dpd": 0},
        {"loan_id": "3", "origination_date": date(2026, 2, 1), "outstanding_principal": 2000, "dpd": 90},
    ]
    result = VintageRollRateService().analyze(rows)
    assert result["vintages"][0]["vintage"] == "2026-01"
    assert result["vintages"][0]["par30"] == 0.25
    assert result["vintages"][1]["par90"] == 1.0


def test_delinquency_buckets_balance_share():
    rows = [
        {"outstanding_principal": 1000, "dpd": 0},
        {"outstanding_principal": 2000, "dpd": 15},
        {"outstanding_principal": 3000, "dpd": 45},
        {"outstanding_principal": 4000, "dpd": 120},
    ]
    result = VintageRollRateService().analyze(rows)
    shares = {item["bucket"]: item["share"] for item in result["buckets"]}
    assert shares["current"] == 0.1
    assert shares["8_30"] == 0.2
    assert shares["31_60"] == 0.3
    assert shares["90_plus"] == 0.4
