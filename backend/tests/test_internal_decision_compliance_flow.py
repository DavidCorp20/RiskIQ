from __future__ import annotations

from copy import deepcopy

from fastapi.testclient import TestClient

from app.main import app
from app.decision.decision_recommendations import (
    DecisionRecommendation,
    DecisionRecommendationRepository,
)
from app.integrations.freshservice import ComplianceAutomationService


class FakeRepo:
    def __init__(self):
        self.rows = []

    def ensure_indexes(self):
        return None

    def ensure_unique_index(self, fields, *, name=None):
        return None

    def ensure_unique_index(self, fields, *, name=None):
        return None

    def find(self, filters=None, limit=100):
        filters = filters or {}
        rows = []
        for row in self.rows:
            if all(row.get(key) == value for key, value in filters.items()):
                rows.append(deepcopy(row))
        return rows[:limit]

    def insert(self, document):
        self.rows.append(deepcopy(document))
        return str(len(self.rows))

    def update(self, filters, update):
        matched = False
        for row in self.rows:
            if all(row.get(key) == value for key, value in filters.items()):
                for key, value in (update.get("$set") or {}).items():
                    row[key] = deepcopy(value)
                for key, value in (update.get("$inc") or {}).items():
                    row[key] = row.get(key, 0) + value
                matched = True
        return matched


def _recommendation() -> DecisionRecommendation:
    return DecisionRecommendation.create(
        dataset_id="dataset-test",
        loan_id="LOAN-001",
        action="preventive_block",
        action_level="high",
        policy_id="ews-action-policy",
        policy_version=1,
        trigger_codes=["DPD_SEVERITY"],
        evidence={"score": 82, "dpd": 95, "balance": 10000},
        rationale="Deterministic EWS critical signal.",
    )


def test_approved_recommendation_writes_immutable_ledger():
    repository = DecisionRecommendationRepository()
    repository.collection = FakeRepo()
    repository.ledger = FakeRepo()
    repository._indexes_ready = False

    saved = repository.save(_recommendation())
    assert saved["status"] == "pending_approval"

    approved = repository.transition(
        saved["recommendation_id"],
        status="approved",
        actor="risk-manager",
        comment="Approved after committee review.",
    )

    assert approved["status"] == "approved"

    ledger = repository.ledger_entries(
        dataset_id="dataset-test",
        recommendation_id=saved["recommendation_id"],
    )
    assert [entry["event"] for entry in reversed(ledger)] == [
        "recommendation_proposed",
        "recommendation_approved",
    ]
    assert all(entry["immutable"] is True for entry in ledger)
    assert ledger[-1]["metadata"]["comment"] == "Approved after committee review."


def test_rejected_recommendation_writes_immutable_ledger():
    repository = DecisionRecommendationRepository()
    repository.collection = FakeRepo()
    repository.ledger = FakeRepo()
    repository._indexes_ready = False

    saved = repository.save(_recommendation())

    rejected = repository.transition(
        saved["recommendation_id"],
        status="rejected",
        actor="risk-manager",
        comment="Rejected because exposure is already under mitigation.",
    )

    assert rejected["status"] == "rejected"

    ledger = repository.ledger_entries(
        recommendation_id=saved["recommendation_id"],
    )
    assert any(entry["event"] == "recommendation_rejected" for entry in ledger)
    assert ledger[-1]["state"] == "rejected"
    assert ledger[-1]["immutable"] is True


def test_compliance_outbox_is_written_when_freshservice_is_disabled(monkeypatch):
    service = ComplianceAutomationService()
    service.outbox = FakeRepo()
    service.sync = FakeRepo()
    service._indexes_ready = False

    from app.config import settings
    monkeypatch.setattr(settings, "freshservice_enabled", False)

    item = service.enqueue(
        event_type="decision_review_transition",
        event={
            "decision_id": "REC-001",
            "dataset_id": "dataset-test",
            "review_state": "approved",
            "actor": "risk-manager",
            "evidence_hash": "abc123",
            "policy_id": "ews-action-policy",
            "policy_version": 1,
        },
        critical=True,
    )

    assert item["status"] == "pending"
    assert item["critical"] is True
    assert item["event"]["decision_id"] == "REC-001"
    assert len(service.outbox.rows) == 1

    import asyncio
    result = asyncio.run(service.process_pending(20))
    assert result["processed"] == 0
    assert service.outbox.rows[0]["status"] == "pending"


def test_decision_recommendation_endpoints_keep_customer_actions_disabled(monkeypatch):
    from app.api import decision_recommendation_routes as routes

    class FakeEWS:
        def summarize(self, rows, high_score=50.0):
            return {
                "available": True,
                "as_of": "2026-09-19",
                "methodology": "portfolio-ews-v1",
                "top_alerts": [{
                    "loan_id": "LOAN-001",
                    "score": 82,
                    "band": "critical",
                    "signals": [{"code": "DPD_SEVERITY"}],
                    "features": {"current_balance": 10000},
                }],
            }

    class FakeEngine:
        POLICY_ID = "ews-action-policy"
        POLICY_VERSION = 1

        def recommend(self, **kwargs):
            return [_recommendation().to_dict()]

    class FakeRecommendationRepository:
        def __init__(self):
            self.items = {}

        def save(self, model):
            item = model.to_dict()
            self.items[model.recommendation_id] = item
            return item

        def transition(self, recommendation_id, *, status, actor, comment):
            item = self.items[recommendation_id]
            item.update({
                "status": status,
                "reviewed_by": actor,
                "review_comment": comment,
            })
            return item

        def list(self, **kwargs):
            return list(self.items.values())

        def ledger_entries(self, **kwargs):
            return [{
                "recommendation_id": key,
                "event": "recommendation_approved",
                "immutable": True,
            } for key in self.items]

    fake_repository = FakeRecommendationRepository()
    monkeypatch.setattr(routes, "ews_service", FakeEWS())
    monkeypatch.setattr(routes, "recommendation_engine", FakeEngine())
    monkeypatch.setattr(routes, "repository", fake_repository)
    monkeypatch.setattr(
        routes,
        "_rows",
        lambda payload: ([{"loan_id": "LOAN-001"}], "dataset-test"),
    )
    monkeypatch.setattr(
        routes.compliance_service,
        "enqueue",
        lambda **kwargs: {
            "status": "pending",
            "event_key": "decision-review-test",
        },
    )
    monkeypatch.setattr(
        routes.compliance_service,
        "process_pending",
        lambda limit=20: None,
    )

    client = TestClient(app)

    response = client.post(
        "/api/v1/decisions/recommend",
        json={"dataset_id": "dataset-test"},
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1
    recommendation_id = response.json()["recommendations"][0]["recommendation_id"]

    response = client.post(
        f"/api/v1/decisions/{recommendation_id}/approve",
        json={
            "actor": "risk-manager",
            "comment": "Approved for internal validation.",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["customer_action_executed"] is False
    assert response.json()["compliance"]["queued"] is True

    response = client.get(
        "/api/v1/decisions/ledger",
        params={"recommendation_id": recommendation_id},
    )
    assert response.status_code == 200
    assert response.json()["immutable"] is True
