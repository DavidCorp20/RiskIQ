from app.analytics.diagnosis import DiagnosisService


def test_diagnosis_builds_evidence_and_next_step() -> None:
    analysis = {
        "posture": {"level": "high", "label": "Riesgo alto"},
        "interpretation": "El segmento B concentra deterioro.",
        "materiality": {"shares": {"par30": 0.12, "par90": 0.03}},
        "concentration": [
            {
                "name": "B",
                "exposure_share": 0.35,
                "par30": 0.22,
                "contribution_to_portfolio_bad_30": 0.51,
                "priority_score": 72,
                "risk_level": "critical",
            }
        ],
        "priorities": [
            {"rank": 1, "type": "concentration", "title": "Revisar B", "evidence": {"par30": 0.22}}
        ],
    }
    readiness = [
        {"model": "Vintage Analysis", "ready": True},
        {"model": "Migration / Roll Rate", "ready": False},
    ]

    result = DiagnosisService().build(
        analysis,
        data_quality={"confidence": "high", "limitation": "Cobertura suficiente."},
        readiness=readiness,
    )

    assert result["status"] == "high"
    assert result["top_driver"]["name"] == "B"
    assert any(item["metric"] == "PAR30" for item in result["evidence"])
    assert result["next_best_analysis"]["model"] == "Vintage Analysis"
    assert result["governance"]["human_review_required"] is True
