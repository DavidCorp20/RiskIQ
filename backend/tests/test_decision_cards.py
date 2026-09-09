from app.decision.decision_cards import DecisionCardService


def test_builds_collection_card_from_recommendation():
    result = DecisionCardService().build([
        {
            "code": "PRIORITIZE_COLLECTIONS",
            "title": "Priorizar cobranza sobre exposición 90+",
            "priority": "critical",
            "rationale": "PAR90 supera el umbral configurado.",
            "evidence": {"par90": 0.01},
            "mode": "suggested",
        }
    ])
    assert len(result) == 1
    card = result[0]
    assert card["category"] == "collections"
    assert card["severity"] == "critical"
    assert card["trigger"] == "PAR90 = 1.00%"
    assert card["status"] == "proposed"
    assert card["mode"] == "suggested"


def test_empty_recommendations_returns_no_cards():
    assert DecisionCardService().build([]) == []
