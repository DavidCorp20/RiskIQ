from app.ai.copilot import RiskCopilotService
from app.analytics.risk_facts import RiskFactsService
from app.analytics.portfolio_history import PortfolioHistoryService
from app.analytics.vintage_rollrate import VintageRollRateService
from app.simulation.scenario_simulator import ScenarioSimulator


def test_risk_facts_thresholds_and_alerts():
    result = RiskFactsService().build({
        "outstanding_balance": 100000,
        "active_loans": 100,
        "par30": 0.08,
        "par60": 0.04,
        "par90": 0.005,
    })
    assert result["summary"]["status"] == "critical"
    assert {a["code"] for a in result["alerts"]} == {"PAR30_HIGH", "PAR90_CRITICAL"}


def test_history_detects_deterioration_without_causality():
    result = PortfolioHistoryService().compare(
        {"snapshot_date": "2026-09-08", "par30": 0.09, "par90": 0.01, "outstanding_balance": 100000},
        {"snapshot_date": "2026-08-08", "par30": 0.07, "par90": 0.005, "outstanding_balance": 95000},
    )
    assert result["status"] == "deteriorating"
    assert {a["code"] for a in result["alerts"]} == {"PAR30_DETERIORATION", "PAR90_DETERIORATION"}
    assert result["causality"] == "not_inferred"


def test_vintage_calculates_vintages_and_refuses_single_snapshot_roll_rate():
    rows = [
        {"origination_date": "2026-01-15", "dpd": 35, "outstanding_principal": 1000},
        {"origination_date": "2026-01-20", "dpd": 0, "outstanding_principal": 1000},
    ]
    result = VintageRollRateService().analyze(rows)
    assert result["vintages"][0]["vintage"] == "2026-01"
    assert result["vintages"][0]["par30"] == 0.5
    assert result["roll_rates"] == []
    assert any("Roll rate requiere snapshots históricos" in w for w in result["warnings"])


def test_scenario_simulator_is_transparent_sensitivity():
    result = ScenarioSimulator().simulate(
        {"balance": 100000, "par30": 0.10, "par90": 0.01},
        {"originations_pct": -0.10, "collection_effectiveness_pct": 0.20},
        "Stress test",
    )
    assert result["baseline"]["balance"] == 100000
    assert result["scenario"]["balance"] == 90000
    assert result["scenario"]["par30"] == 0.08
    assert result["scenario"]["par90"] == 0.008
    assert "no constituye una predicción ML" in result["interpretation"]


def test_copilot_accepts_canonical_risk_facts_list():
    result = RiskCopilotService().answer(
        "¿Qué está pasando?",
        {
            "facts": [
                {"id": "par30", "label": "PAR30", "value": 8.7, "unit": "percent"},
                {"id": "portfolio_size", "label": "Exposición activa", "value": 100000, "unit": "currency"},
            ],
            "alerts": [{"code": "PAR30_HIGH"}],
            "summary": {"status": "critical"},
        },
    )
    assert result["grounded"] is True
    assert result["status"] == "critical"
    assert any("PAR30: 8.7percent" == line for line in result["evidence"])
