import pytest
from app.predictive.validation import auc_gini_ks, brier_score, calibration_curve, psi, validate_model


def test_discrimination_metrics_are_deterministic():
    result = auc_gini_ks([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1])
    assert result["auc"] == pytest.approx(1.0)
    assert result["gini"] == pytest.approx(1.0)
    assert result["ks"] == pytest.approx(1.0)


def test_brier_and_calibration():
    assert brier_score([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1]) == pytest.approx(0.025)
    curve = calibration_curve([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1], bins=2)
    assert len(curve) == 2
    assert curve[0]["observed"] == pytest.approx(0.0)
    assert curve[1]["observed"] == pytest.approx(1.0)


def test_psi_zero_for_identical_population():
    assert psi([1, 2, 3, 4], [1, 2, 3, 4]) == pytest.approx(0.0)


def test_validation_contract():
    result = validate_model(
        model_id="pd-v1",
        model_version="1.0",
        validation_window="2026-Q3",
        scores=[0.1, 0.2, 0.8, 0.9],
        labels=[0, 0, 1, 1],
    )
    assert result["contract"] == "risk-intelligence-v1"
    assert result["status"] == "PASS"
