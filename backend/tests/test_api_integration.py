from __future__ import annotations

import io
import json

from fastapi.testclient import TestClient

from app.main import app
import app.api.data_routes as data_routes
import app.api.dataset_intelligence_routes as dataset_routes


class FakeCollection:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    def find(self, query=None, limit=None):
        query = query or {}
        result = [
            row for row in self.rows
            if all(row.get(key) == value for key, value in query.items())
        ]
        return result[:limit] if limit else result

    def insert(self, document):
        row = dict(document)
        row.setdefault("id", f"snapshot-{len(self.rows) + 1}")
        self.rows.append(row)
        return row["id"]


class FakePersistence:
    def __init__(self, dataset_id="api-e2e"):
        self.datasets = FakeCollection([{"dataset_id": dataset_id, "source_name": "demo.csv"}])
        self.portfolio_records = FakeCollection([
            {
                "dataset_id": dataset_id,
                "customer_id": "C001",
                "loan_id": "L001",
                "outstanding_principal": 1000,
                "scheduled_amount": 500,
                "paid_amount": 0,
                "due_date": "2026-08-01",
                "segment": "retail",
                "dpd": 45,
                "origination_date": "2026-05-01",
                "status": "active",
            },
            {
                "dataset_id": dataset_id,
                "customer_id": "C002",
                "loan_id": "L002",
                "outstanding_principal": 2000,
                "scheduled_amount": 1000,
                "paid_amount": 900,
                "due_date": "2026-09-01",
                "segment": "retail",
                "dpd": 8,
                "origination_date": "2026-07-01",
                "status": "active",
            },
            {
                "dataset_id": dataset_id,
                "customer_id": "C003",
                "loan_id": "L003",
                "outstanding_principal": 1500,
                "scheduled_amount": 750,
                "paid_amount": 0,
                "due_date": "2026-05-01",
                "segment": "micro",
                "dpd": 100,
                "origination_date": "2026-02-01",
                "status": "active",
            },
        ])
        self.customers = FakeCollection([
            {"dataset_id": dataset_id, "id": "C001"},
            {"dataset_id": dataset_id, "id": "C002"},
            {"dataset_id": dataset_id, "id": "C003"},
        ])
        self.loans = FakeCollection([
            {"dataset_id": dataset_id, "id": "L001", "customer_id": "C001", "outstanding_principal": 1000, "status": "active", "dpd": 45},
            {"dataset_id": dataset_id, "id": "L002", "customer_id": "C002", "outstanding_principal": 2000, "status": "active", "dpd": 8},
            {"dataset_id": dataset_id, "id": "L003", "customer_id": "C003", "outstanding_principal": 1500, "status": "active", "dpd": 100},
        ])
        self.installments = FakeCollection([])
        self.payments = FakeCollection([])
        self.snapshots = FakeCollection([])


def test_health_endpoint() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "riskiq-api"}


def test_discover_endpoint_accepts_csv() -> None:
    csv = "customer_code,loan_number,balance,days_late\nC001,L001,1000,45\n"
    response = TestClient(app).post(
        "/api/v1/data/discover",
        files={"file": ("portfolio.csv", io.BytesIO(csv.encode()), "text/csv")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["row_count"] == 1
    assert body["column_count"] == 4
    assert body["coverage_score"] > 0


def test_ingest_endpoint_blocks_quality_failure(monkeypatch) -> None:
    class QualityBlocked:
        def assess(self, rows):
            return {"status": "blocked", "quality_score": 0, "checks": []}

    monkeypatch.setattr(data_routes, "quality", QualityBlocked())
    csv = "customer_id,loan_id,outstanding_principal\n,,1000\n"
    mappings = json.dumps([
        {"source": "customer_id", "target": "customer_id", "required": True},
        {"source": "loan_id", "target": "loan_id", "required": True},
        {"source": "outstanding_principal", "target": "outstanding_principal", "required": False},
    ])
    response = TestClient(app).post(
        "/api/v1/data/ingest",
        files={"file": ("bad.csv", io.BytesIO(csv.encode()), "text/csv")},
        data={"mappings": mappings},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["persistence_blocked"] is True
    assert detail["quality"]["status"] == "blocked"


def test_dataset_run_endpoint_returns_unified_contract(monkeypatch) -> None:
    fake = FakePersistence()
    monkeypatch.setattr(dataset_routes, "persistence", fake)

    response = TestClient(app).post(
        "/api/v1/datasets/api-e2e/run",
        json={"snapshot_date": "2026-09-09"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == "dataset-intelligence-v3"
    assert body["dataset_id"] == "api-e2e"
    assert body["snapshot"]["active_loans"] == 3
    assert float(body["snapshot"]["outstanding_balance"]) == 4500
    assert body["risk_analytics"]["npl"]["available"] is True
    assert body["risk_analytics"]["npl"]["regulatory_definition"] is False
    assert body["vintage"]["roll_rate_available"] is False
    assert body["governance"]["trend_available"] is False
    assert body["governance"]["customer_actions_executed"] is False


def test_dataset_run_uses_previous_snapshot_for_trend(monkeypatch) -> None:
    fake = FakePersistence()
    fake.snapshots.rows.append({
        "id": "snapshot-old",
        "dataset_id": "api-e2e",
        "snapshot_date": "2026-09-08",
        "active_loans": 3,
        "outstanding_balance": 4600,
        "par7": 0,
        "par30": 0.05,
        "par60": 0.05,
        "par90": 0,
    })
    monkeypatch.setattr(dataset_routes, "persistence", fake)

    response = TestClient(app).post(
        "/api/v1/datasets/api-e2e/run",
        json={"snapshot_date": "2026-09-09"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["previous_snapshot"]["id"] == "snapshot-old"
    assert body["governance"]["trend_available"] is True
    assert body["workspace"]["decision_center"]["trend"]["status"] in {"deteriorating", "improving", "stable"}
