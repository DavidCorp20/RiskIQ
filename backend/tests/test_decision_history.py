from app.analytics.learning_loop import DecisionLearningService
from app.audit.decision_history import DecisionHistoryService


def test_decision_can_be_recorded_and_resolved():
    service = DecisionHistoryService()
    entry = service.record({
        "id": "decision-1",
        "code": "PRIORITIZE_COLLECTIONS",
        "title": "Priorizar cobranza",
        "evidence": {"par90": 0.01},
        "recommendation": "Priorizar cobranza",
        "rationale": "PAR90 elevado",
    }, actor="risk-analyst")
    assert entry["status"] == "proposed"
    resolved = service.resolve("decision-1", {"improved": True, "par90_after": 0.007})
    assert resolved["status"] == "resolved"
    assert resolved["outcome"]["improved"] is True


def test_learning_summary_is_descriptive():
    result = DecisionLearningService().summarize([
        {"status": "resolved", "outcome": {"improved": True}},
        {"status": "resolved", "outcome": {"improved": False}},
        {"status": "proposed", "outcome": None},
    ])
    assert result["resolved_decisions"] == 2
    assert result["improvement_rate"] == 0.5
    assert "causal" in result["methodology"]
