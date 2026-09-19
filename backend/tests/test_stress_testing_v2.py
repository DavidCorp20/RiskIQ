import pytest
from app.stress_testing.stress_v2 import run_macro_stress


def test_without_validated_correlation_projection_stays_at_baseline():
    result = run_macro_stress(
        base_pd=0.10,
        base_lgd=0.40,
        base_ead=100000,
        profile="LATAM_CONSERVATIVE",
        elasticities={"pd": {"inflation": 0.5}},
        validation={"inflation": {"validated": False, "coefficient": 0.9, "p_value": 0.01, "sample_size": 100}},
    )
    assert result["stressed"]["pd"] == pytest.approx(0.10)
    assert result["impact"]["incremental_expected_loss"] == pytest.approx(0.0)


def test_validated_elasticity_changes_expected_loss_deterministically():
    result = run_macro_stress(
        base_pd=0.10,
        base_lgd=0.40,
        base_ead=100000,
        profile="LATAM_CONSERVATIVE",
        elasticities={"pd": {"inflation": 0.5}},
        validation={"inflation": {"validated": True, "coefficient": 0.6, "p_value": 0.01, "sample_size": 24}},
    )
    assert result["stressed"]["pd"] > result["baseline"]["pd"]
    assert result["stressed"]["expected_loss"] > result["baseline"]["expected_loss"]
    assert result["run_id"]
