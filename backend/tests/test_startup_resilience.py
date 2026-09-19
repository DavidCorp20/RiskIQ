from app.core import startup


def test_liveness_is_independent_from_dependencies():
    startup.runtime_state.status = "degraded"
    payload = startup.liveness()
    assert payload["status"] == "ok"
    assert payload["runtime"] == "degraded"


def test_readiness_reports_degraded_without_claiming_ready():
    startup.runtime_state.mongo = "degraded"
    startup.runtime_state.status = "degraded"
    startup.runtime_state.checks = {"mongo": "degraded:ConnectionError"}
    payload = startup.readiness()
    assert payload["ready"] is False
    assert payload["status"] == "degraded"


def test_version_contract():
    payload = startup.version()
    assert payload["contract"] == "risk-intelligence-v1"
    assert payload["service"] == "riskiq-api"
