from __future__ import annotations

from app.api.schemas import DecisionRule, RuleAction, RuleCondition
from app.engine.decision_engine import DecisionEngine


def test_decision_engine_enqueues_compliance_for_audited_execution(monkeypatch):
    events = []

    monkeypatch.setattr(
        "app.engine.decision_engine.compliance_service.enqueue",
        lambda **kwargs: events.append(kwargs),
    )

    rule = DecisionRule(
        id="POLICY-001",
        name="High PAR",
        version=3,
        conditions=[RuleCondition(field="par30", operator="gte", value=0.10)],
        actions=[
            RuleAction(
                type="decision",
                parameters={"outcome": "REVIEW"},
            )
        ],
    )

    result = DecisionEngine().evaluate(
        {"par30": 0.18, "outstanding_balance": 100000},
        [rule],
        audit=True,
        actor="risk-manager",
        dataset_id="dataset-1",
        snapshot_id="snapshot-1",
        business_id="business-1",
    )

    assert result["decision"] == "REVIEW"
    assert result["audit_enqueued"] is True
    assert result["decision_id"]
    assert len(events) == 1
    assert events[0]["event_type"] == "decision_execution"
    assert events[0]["event"]["policy_id"] == "POLICY-001"
    assert events[0]["event"]["policy_version"] == 3
    assert events[0]["event"]["actor"] == "risk-manager"
    assert events[0]["event"]["evidence"]["dataset_id"] == "dataset-1"


def test_decision_engine_does_not_enqueue_compliance_for_sandbox_execution(monkeypatch):
    events = []

    monkeypatch.setattr(
        "app.engine.decision_engine.compliance_service.enqueue",
        lambda **kwargs: events.append(kwargs),
    )

    rule = DecisionRule(
        id="POLICY-002",
        name="High PAR",
        conditions=[RuleCondition(field="par30", operator="gte", value=0.10)],
        actions=[
            RuleAction(
                type="decision",
                parameters={"outcome": "REVIEW"},
            )
        ],
    )

    result = DecisionEngine().evaluate(
        {"par30": 0.18},
        [rule],
        audit=False,
    )

    assert result["decision"] == "REVIEW"
    assert result["audit_enqueued"] is False
    assert events == []
