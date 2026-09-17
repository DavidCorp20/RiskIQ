import pytest

from app.analytics.risk_analytics import RiskAnalyticsIntegrityError, RiskAnalyticsService


@pytest.fixture
def service():
    return RiskAnalyticsService()


def test_risk_analytics_uses_outstanding_exposure_and_dpd_buckets(service):
    rows = [
        {"loan_id": "L1", "outstanding_principal": 100, "dpd": 0, "segment": "A", "product_id": "P1", "origination_date": "2026-01-10"},
        {"loan_id": "L2", "outstanding_principal": 200, "dpd": 10, "segment": "A", "product_id": "P1", "origination_date": "2026-01-10"},
        {"loan_id": "L3", "outstanding_principal": 300, "dpd": 35, "segment": "B", "product_id": "P2", "origination_date": "2026-02-10"},
        {"loan_id": "L4", "outstanding_principal": 400, "dpd": 95, "segment": "B", "product_id": "P2", "origination_date": "2026-02-10"},
    ]

    result = service.analyze(rows)

    assert result["loan_count"] == 4
    assert result["exposure"] == 1000
    assert result["par"]["par7"]["ratio"] == 0.9
    assert result["par"]["par30"]["ratio"] == 0.7
    assert result["par"]["par60"]["ratio"] == 0.4
    assert result["par"]["par90"]["ratio"] == 0.4
    assert result["methodology"]["deterministic"] is True
    assert result["methodology"]["causality_inferred"] is False


def test_risk_analytics_returns_zero_ratios_for_zero_exposure(service):
    result = service.analyze([
        {"outstanding_principal": 0, "dpd": 120, "segment": "A"},
        {"outstanding_principal": 0, "dpd": 0, "segment": "B"},
    ])

    assert result["available"] is False
    assert result["loan_count"] == 0
    assert result["exposure"] == 0
    assert all(bucket["ratio"] == 0 for bucket in result["par"].values())
    assert result["integrity"] == {
        "exposure_reconciled": True,
        "cumulative_par_monotonic": True,
        "non_negative": True,
        "duplicate_keys": [],
        "concentration_valid": True,
    }


def test_risk_analytics_flags_evidence_backed_concentration_driver(service):
    rows = [
        {"outstanding_principal": 900, "dpd": 40, "segment": "HighRisk", "product_id": "P1"},
        {"outstanding_principal": 100, "dpd": 0, "segment": "Other", "product_id": "P2"},
    ]

    result = service.analyze(rows)

    assert result["drivers"]
    assert result["drivers"][0]["id"] == "segment:HighRisk"
    assert result["drivers"][0]["confidence"] == "deterministic"
    assert result["drivers"][0]["exposure_share"] == 0.9


def test_integrity_buckets_reconcile_exactly(service):
    result = service.analyze([
        {"loan_id": "L1", "outstanding_principal": 100.00, "dpd": 0},
        {"loan_id": "L2", "outstanding_principal": 125.50, "dpd": 15},
        {"loan_id": "L3", "outstanding_principal": 200.25, "dpd": 30},
        {"loan_id": "L4", "outstanding_principal": 75.25, "dpd": 60},
        {"loan_id": "L5", "outstanding_principal": 50.00, "dpd": 90},
    ])

    buckets = result["dpd_buckets"]
    assert buckets["current"]["balance"] == 100.00
    assert buckets["dpd_1_29"]["balance"] == 125.50
    assert buckets["dpd_30_59"]["balance"] == 200.25
    assert buckets["dpd_60_89"]["balance"] == 75.25
    assert buckets["dpd_90_plus"]["balance"] == 50.00
    assert sum(item["balance"] for item in buckets.values()) == result["exposure"]
    assert result["integrity"]["exposure_reconciled"] is True


def test_integrity_par_is_derived_from_discrete_buckets(service):
    result = service.analyze([
        {"loan_id": "L1", "outstanding_principal": 100, "dpd": 0},
        {"loan_id": "L2", "outstanding_principal": 200, "dpd": 10},
        {"loan_id": "L3", "outstanding_principal": 300, "dpd": 35},
        {"loan_id": "L4", "outstanding_principal": 400, "dpd": 70},
        {"loan_id": "L5", "outstanding_principal": 500, "dpd": 95},
    ])

    buckets = result["dpd_buckets"]
    assert result["par"]["par30"]["balance"] == 1200
    assert result["par"]["par60"]["balance"] == 900
    assert result["par"]["par90"]["balance"] == 500
    assert result["par"]["par30"]["balance"] == (
        buckets["dpd_30_59"]["balance"]
        + buckets["dpd_60_89"]["balance"]
        + buckets["dpd_90_plus"]["balance"]
    )
    assert result["par"]["par60"]["balance"] == (
        buckets["dpd_60_89"]["balance"] + buckets["dpd_90_plus"]["balance"]
    )
    assert result["par"]["par90"]["balance"] == buckets["dpd_90_plus"]["balance"]
    assert result["integrity"]["cumulative_par_monotonic"] is True


def test_integrity_duplicate_loan_and_snapshot_is_rejected(service):
    rows = [
        {"loan_id": "L1", "snapshot_date": "2026-09-01", "outstanding_principal": 100, "dpd": 0},
        {"loan_id": "L1", "snapshot_date": "2026-09-01", "outstanding_principal": 90, "dpd": 5},
    ]

    with pytest.raises(RiskAnalyticsIntegrityError, match="Duplicate loan_id"):
        service.analyze(rows)


def test_integrity_same_loan_on_different_snapshots_is_valid(service):
    rows = [
        {"loan_id": "L1", "snapshot_date": "2026-08-01", "outstanding_principal": 100, "dpd": 0},
        {"loan_id": "L1", "snapshot_date": "2026-09-01", "outstanding_principal": 80, "dpd": 10},
    ]

    result = service.analyze(rows)

    assert result["snapshot"] == "2026-09-01"
    assert result["loan_count"] == 1
    assert result["exposure"] == 80
    assert result["dpd_buckets"]["dpd_1_29"]["balance"] == 80


def test_integrity_par_equality_is_valid_when_intermediate_buckets_are_zero(service):
    result = service.analyze([
        {"loan_id": "L1", "outstanding_principal": 500, "dpd": 0},
        {"loan_id": "L2", "outstanding_principal": 300, "dpd": 95},
    ])

    assert result["par"]["par30"]["balance"] == 300
    assert result["par"]["par60"]["balance"] == 300
    assert result["par"]["par90"]["balance"] == 300
    assert result["dpd_buckets"]["dpd_30_59"]["balance"] == 0
    assert result["dpd_buckets"]["dpd_60_89"]["balance"] == 0
    assert result["integrity"]["concentration_valid"] is True


def test_integrity_par_equality_is_invalid_when_intermediate_bucket_exists(service):
    buckets = {
        "current": {"balance": 100, "loans": 1},
        "dpd_1_29": {"balance": 0, "loans": 0},
        "dpd_30_59": {"balance": 50, "loans": 1},
        "dpd_60_89": {"balance": 0, "loans": 0},
        "dpd_90_plus": {"balance": 50, "loans": 1},
    }
    par = {
        "par30": {"balance": 50},
        "par60": {"balance": 50},
        "par90": {"balance": 50},
    }

    with pytest.raises(RiskAnalyticsIntegrityError, match="PAR equality"):
        service._validate_integrity(200, buckets, par)


def test_integrity_negative_outstanding_principal_is_rejected(service):
    with pytest.raises(RiskAnalyticsIntegrityError, match="Negative outstanding_principal"):
        service.analyze([
            {"loan_id": "L1", "outstanding_principal": -10, "dpd": 0},
            {"loan_id": "L2", "outstanding_principal": 100, "dpd": 0},
        ])
