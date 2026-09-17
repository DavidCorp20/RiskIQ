from fastapi.testclient import TestClient

from app.api.schemas import DecisionRule, RuleAction, RuleCondition
from app.engine.decision_engine import DecisionEngine
from app.analytics.decision_engine import DecisionEngineService, RiskDecisionEngine
from app.api.v1.endpoints import decisions as decisions_endpoint
from app.main import app


client = TestClient(app)


def test_rule_triggers_when_all_conditions_match() -> None:
    rule = DecisionRule(
        id="par30-high",
        name="High PAR30",
        conditions=[RuleCondition(field="par30", operator="gt", value=0.08)],
        actions=[RuleAction(type="create_alert", parameters={"severity": "high"})],
    )

    result = DecisionEngine().evaluate({"par30": 0.10}, [rule])

    assert result["triggered_rules"] == ["par30-high"]
    assert result["actions"][0]["type"] == "create_alert"


def test_rule_does_not_trigger_when_condition_fails() -> None:
    rule = DecisionRule(
        id="par30-high",
        name="High PAR30",
        conditions=[RuleCondition(field="par30", operator="gt", value=0.08)],
    )

    result = DecisionEngine().evaluate({"par30": 0.05}, [rule])

    assert result["triggered_rules"] == []
    assert result["actions"] == []


def _risk(par30=0.0, par60=0.0, par90=0.0, exposure=1000):
    return {"available": True, "exposure": exposure, "par": {
        "par30": {"ratio": par30}, "par60": {"ratio": par60}, "par90": {"ratio": par90}
    }}


def test_risk_decision_engine_prioritizes_critical_and_requires_human_review() -> None:
    result = DecisionEngineService().build(_risk(par30=0.10, par90=0.02))
    first = result["decisions"][0]
    assert first["id"] == "par90_review"
    assert first["severity"] == "critical"
    assert first["requires_human_review"] is True
    assert first["executed"] is False
    assert result["cards"][0]["recommended_action"]


def test_risk_decision_engine_detects_bucket_inconsistency() -> None:
    result = DecisionEngineService().build(_risk(par30=0.10, par60=0.20))
    item = next(x for x in result["decisions"] if x["id"] == "bucket_inconsistency")
    assert item["severity"] == "critical"


def test_risk_decision_engine_translates_npl_proxy() -> None:
    result = DecisionEngineService().build(_risk(), {"available": True, "ratio": 0.06, "definition": "NPL90_proxy"})
    item = next(x for x in result["decisions"] if x["id"] == "npl_review")
    assert item["severity"] == "high"
    assert "regulatory_definition=false" in item["evidence"]


def test_risk_decision_engine_has_monitoring_card_when_healthy() -> None:
    result = DecisionEngineService().build(_risk())
    assert result["decisions"][0]["id"] == "portfolio_monitor"
    assert result["decisions"][0]["severity"] == "low"
    assert result["governance"]["customer_actions_executed"] is False


def analytics_payload(*, par30=0.0, deterioration_rate=None, integrity=None):
    drivers = []
    if deterioration_rate is not None:
        drivers.append({
            "dimension": "segment",
            "key": "retail",
            "label": "Segmento retail",
            "to_30_plus_rate": deterioration_rate,
        })
    return {
        "available": True,
        "exposure": 100000.0,
        "par": {"par30": {"ratio": par30}},
        "integrity": integrity or {"exposure_reconciled": True, "non_negative": True},
        "deterioration_drivers": drivers,
    }


def test_policy_par30_warning_and_critical_thresholds() -> None:
    engine = RiskDecisionEngine()

    warning = engine.evaluate(analytics_payload(par30=0.075), dataset_id="ds-1")
    assert warning["overall_status"] == "FLAGGED"
    assert warning["triggered_rules"][0]["rule_id"] == "R101_PAR30_HIGH"
    assert warning["triggered_rules"][0]["severity"] == "WARNING"

    critical = engine.evaluate(analytics_payload(par30=0.101), dataset_id="ds-1")
    assert critical["overall_status"] == "FLAGGED"
    assert critical["triggered_rules"][0]["severity"] == "CRITICAL"


def test_policy_deterioration_spike_triggers_critical() -> None:
    result = RiskDecisionEngine().evaluate(
        analytics_payload(deterioration_rate=0.031), dataset_id="ds-2"
    )
    rule = next(rule for rule in result["triggered_rules"] if rule["rule_id"] == "R102_MIGRATION_DETERIORATION_SPIKE")
    assert rule["severity"] == "CRITICAL"
    assert rule["metric_value"] == 0.031


def test_policy_integrity_failure_requires_action() -> None:
    result = RiskDecisionEngine().evaluate(
        analytics_payload(integrity={"exposure_reconciled": False, "non_negative": True}),
        dataset_id="ds-3",
    )
    assert result["overall_status"] == "ACTION_REQUIRED"
    rule = next(rule for rule in result["triggered_rules"] if rule["rule_id"] == "R103_INTEGRITY_FAIL")
    assert rule["severity"] == "CRITICAL"
    assert rule["metric_value"] == "exposure_reconciled"


def test_policy_healthy_payload_is_approved() -> None:
    result = RiskDecisionEngine().evaluate(
        analytics_payload(par30=0.05, deterioration_rate=0.03), dataset_id="ds-4"
    )
    assert result["overall_status"] == "APPROVED"
    assert result["triggered_rules"] == []
    assert result["recommended_actions"] == []


def test_post_evaluate_direct_payload() -> None:
    response = client.post(
        "/api/v1/risk/decisions/evaluate",
        json={"dataset_id": "ds-direct", "payload": analytics_payload(par30=0.06)},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["dataset_id"] == "ds-direct"
    assert body["result_id"] is None
    assert body["overall_status"] == "FLAGGED"
    assert body["triggered_rules"][0]["rule_id"] == "R101_PAR30_HIGH"


def test_post_evaluate_persisted_result(monkeypatch) -> None:
    class FakeRepository:
        def get_analysis_by_id(self, result_id: str):
            assert result_id == "result-001"
            return {
                "result_id": result_id,
                "dataset_id": "ds-persisted",
                "payload": analytics_payload(par30=0.11),
            }

    monkeypatch.setattr(decisions_endpoint, "RiskAnalysisRepository", FakeRepository)
    response = client.post(
        "/api/v1/risk/decisions/evaluate", json={"result_id": "result-001"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["dataset_id"] == "ds-persisted"
    assert body["result_id"] == "result-001"
    assert body["overall_status"] == "FLAGGED"
    assert body["triggered_rules"][0]["severity"] == "CRITICAL"


def test_post_evaluate_persisted_result_not_found(monkeypatch) -> None:
    class FakeRepository:
        def get_analysis_by_id(self, result_id: str):
            return None

    monkeypatch.setattr(decisions_endpoint, "RiskAnalysisRepository", FakeRepository)
    response = client.post(
        "/api/v1/risk/decisions/evaluate", json={"result_id": "missing"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Analysis result not found"
