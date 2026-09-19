from app.simulation.scenario_simulator import ScenarioSimulator


def test_mvp_stress_uses_percentage_point_shock():
    result = ScenarioSimulator().simulate(
        {"balance": 45500, "par30": 0.4835, "par90": 0.4835},
        {"par_shock_points": 0.05},
        "Stress +5 pp",
    )
    assert result["baseline"]["par30"] == 0.4835
    assert result["scenario"]["par30"] == 0.5335
    assert result["scenario"]["par90"] == 0.5335
    assert result["delta"]["par30"] == 0.05
    assert result["impact"]["par30_delta_pp"] == 5.0
    assert result["assumptions"]["par_shock_unit"] == "percentage_points"


def test_legacy_shock_alias_is_not_silent_noop():
    result = ScenarioSimulator().simulate(
        {"balance": 100000, "par30": 0.10, "par90": 0.02},
        {"shock_pct": 0.05},
        "Legacy shock",
    )
    assert result["scenario"]["par30"] == 0.15
    assert result["scenario"]["par90"] == 0.07
