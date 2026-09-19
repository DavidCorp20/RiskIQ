from app.simulation.scenario_simulator import ScenarioSimulator


def test_scenario_reduces_balance_and_delinquency():
    result = ScenarioSimulator().simulate(
        {"balance": 100000, "par30": 0.10, "par90": 0.02},
        {"originations_pct": -0.20, "collection_effectiveness_pct": 0.10},
        "Reduce originations",
    )
    assert result["scenario"]["balance"] == 80000
    assert result["scenario"]["par30"] == 0.09
    assert result["scenario"]["par90"] == 0.018
    assert "no constituye una predicción ML" in result["interpretation"]
