from app.predictive.transition_engine import TransitionEngine
from app.predictive.survival_engine import SurvivalEngine
from app.predictive.pd_engine import PDEngine

def rows():
    return [
        {"loan_id":"1","snapshot_date":"2026-01","dpd":0},
        {"loan_id":"1","snapshot_date":"2026-02","dpd":35},
        {"loan_id":"1","snapshot_date":"2026-03","dpd":95},
        {"loan_id":"2","snapshot_date":"2026-01","dpd":0},
        {"loan_id":"2","snapshot_date":"2026-02","dpd":10},
        {"loan_id":"2","snapshot_date":"2026-03","dpd":20},
    ]

def test_transition_and_pd_are_deterministic():
    matrix=TransitionEngine().build_matrix(rows())
    assert matrix.sample_size == 4
    assert TransitionEngine().project_pd(matrix,1)["early_30_59"] == 1.0

def test_survival_curve_is_monotonic():
    curve=SurvivalEngine().kaplan_meier([
        {"duration":1,"default":0},
        {"duration":2,"default":1},
        {"duration":3,"default":0},
    ])
    assert curve.points[-1].survival <= curve.points[0].survival

def test_metrics():
    result=PDEngine().validation_metrics([.1,.2,.8,.9],[0,0,1,1])
    assert result["auc"] == 1.0
    assert result["gini"] == 1.0
