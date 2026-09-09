from app.ai.copilot import RiskCopilotService


def test_copilot_uses_supplied_evidence_without_inventing_facts():
    result = RiskCopilotService().answer(
        "¿Por qué aumentó la mora?",
        {
            "facts": {"par30": {"label": "PAR30", "value": 0.087, "unit": ""}},
            "alerts": [{"code": "PAR30_HIGH"}],
            "summary": {"status": "critical"},
        },
        drivers=[{"key": "segment-c", "evidence": {"par30": 0.12}}],
    )
    assert result["grounded"] is True
    assert result["status"] == "critical"
    assert result["evidence"] == ["PAR30: 0.087"]
    assert "asociativa" in result["answer"]
