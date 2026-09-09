from app.analytics.npl import NPLAnalyticsService
from app.analytics.portfolio_intelligence import PortfolioIntelligenceService
from app.analytics.risk_drivers import RiskDriverEngine
from app.analytics.snapshot_engine import SnapshotEngine


def sample_rows():
    return [
        {"customer_id": "C1", "loan_id": "L1", "segment": "A", "dpd": 10, "outstanding_principal": 1000},
        {"customer_id": "C2", "loan_id": "L2", "segment": "B", "dpd": 95, "outstanding_principal": 2000},
        {"customer_id": "C3", "loan_id": "L3", "segment": "B", "dpd": 0, "outstanding_principal": 1000},
    ]


def test_npl_proxy_90_plus_dpd():
    result = NPLAnalyticsService().analyze(sample_rows())
    assert result["available"] is True
    assert result["balance"] == 2000.0
    assert result["ratio"] == 0.5
    assert result["affected_loans"] == 1
    assert result["regulatory_definition"] is False


def test_portfolio_intelligence_exposes_segments():
    result = PortfolioIntelligenceService().analyze(sample_rows())
    portfolio = result["portfolio"]
    assert portfolio["loans"] == 3
    assert portfolio["balance"] == 4000
    assert portfolio["par30"] == 0.5
    assert portfolio["par90"] == 0.5
    segment_b = next(s for s in result["segments"] if s["segment"] == "B")
    assert segment_b["share_of_portfolio"] == 0.75
    assert segment_b["par90"] == round(2000 / 3000, 4)


def test_risk_driver_is_associative_and_ranked():
    analysis = {
        "portfolio": {"par30": 0.10},
        "segments": [
            {"segment": "B", "par30": 0.20, "share_of_portfolio": 0.50, "loans": 100, "balance": 5000},
            {"segment": "A", "par30": 0.15, "share_of_portfolio": 0.20, "loans": 40, "balance": 2000},
        ],
    }
    result = RiskDriverEngine().build(analysis)
    assert len(result) == 2
    assert result[0]["key"] == "B"
    assert result[0]["causality"] == "associative"
    assert result[0]["confidence"] == "high"


def test_snapshot_engine_builds_point_in_time_metrics():
    loans = [
        {"loan_id": "L1", "customer_id": "C1", "status": "active", "outstanding_principal": 1000},
        {"loan_id": "L2", "customer_id": "C2", "status": "active", "outstanding_principal": 2000},
    ]
    installments = [
        {"installment_id": "I1", "loan_id": "L1", "due_date": "2026-09-01", "scheduled_amount": 100, "paid_amount": 0},
        {"installment_id": "I2", "loan_id": "L2", "due_date": "2026-08-01", "scheduled_amount": 100, "paid_amount": 0},
    ]
    result = SnapshotEngine().build(loans, installments, "2026-09-08", "test")
    assert result["active_loans"] == 2
    assert result["outstanding_balance"] == 3000
    assert result["par7"] == 1.0
    assert result["par30"] == 2000 / 3000
    assert result["par60"] == 0.0
    assert result["par90"] == 0.0
    assert result["metric_basis"] == "balance-weighted outstanding principal"
