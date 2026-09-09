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
    assert result["total_loans"] == 3
    assert result["total_balance"] == 4000
    assert result["portfolio_par30"] == 0.5
    assert result["portfolio_par90"] == 0.5
    assert any(s["segment"] == "B" for s in result["segments"])


def test_snapshot_engine_is_point_in_time():
    loans = [
        {"loan_id": "L1", "status": "active", "outstanding_principal": 1000},
        {"loan_id": "L2", "status": "active", "outstanding_principal": 2000},
    ]
    installments = [
        {"loan_id": "L1", "due_date": "2026-09-01", "scheduled_amount": 100, "paid_amount": 0},
        {"loan_id": "L2", "due_date": "2026-08-01", "scheduled_amount": 100, "paid_amount": 0},
    ]
    result = SnapshotEngine().build(loans, installments, "2026-09-08", "test")
    assert result["active_loans"] == 2
    assert result["outstanding_balance"] == 3000
    assert result["metric_basis"] == "balance-weighted outstanding principal"


def test_risk_drivers_do_not_claim_causality():
    analysis = {
        "portfolio_par30": 0.10,
        "segments": [
            {"segment": "B", "par30": 0.20, "share_of_portfolio": 0.50, "loans": 100, "balance": 5000}
        ],
    }
    result = RiskDriverEngine().build(analysis)
    assert result
    assert result[0]["causality"] == "associative"
