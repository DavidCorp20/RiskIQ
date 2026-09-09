from app.analytics.risk_facts import RiskFactsService


def test_high_par30_creates_high_risk_alert():
    result = RiskFactsService().build({
        "active_loans": 100,
        "outstanding_balance": 250000,
        "par30": 0.10,
        "par60": 0.04,
        "par90": 0.01,
    })

    assert result["summary"]["status"] == "critical"
    assert any(alert["code"] == "PAR30_HIGH" for alert in result["alerts"])


def test_healthy_portfolio_has_no_alerts():
    result = RiskFactsService().build({
        "active_loans": 50,
        "outstanding_balance": 100000,
        "par30": 0,
        "par60": 0,
        "par90": 0,
    })

    assert result["summary"]["status"] == "healthy"
    assert result["alerts"] == []
