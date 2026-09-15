from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.dataset_intelligence_routes import router as dataset_router
from app.api.dataset_registry_routes import router as dataset_registry_router
from app.main import app

# Keep the integration fixture intentionally in-memory for deterministic API
# contract tests. Decision evidence is exercised against the CI Mongo service.

class FakeCollection:
    def __init__(self):
        self.rows = []

    def create_index(self, *args, **kwargs):
        return "idx"

    def insert_one(self, document):
        self.rows.append(dict(document))
        class Result:
            inserted_id = "fake-id"
        return Result()

    def find(self, filters=None, projection=None):
        filters = filters or {}
        rows = [r for r in self.rows if all(r.get(k) == v for k, v in filters.items())]
        class Cursor(list):
            def limit(self, n):
                return Cursor(self[:n])
        return Cursor(rows)

    def update_one(self, filters, update):
        for row in self.rows:
            if all(row.get(k) == v for k, v in filters.items()):
                row.update(update.get("$set", update))
                class Result:
                    matched_count = 1
                return Result()
        class Result:
            matched_count = 0
        return Result()

class FakePersistence:
    def __init__(self):
        self.snapshots = FakeCollection()
        self.datasets = FakeCollection()
        self.records = FakeCollection()
        self.snapshots.rows.extend([
            {"id": "s1", "dataset_id": "api-e2e", "snapshot_date": "2026-09-07", "active_loans": 2, "outstanding_balance": 3000, "par7": 0, "par30": 0.02, "par60": 0, "par90": 0},
            {"id": "s2", "dataset_id": "api-e2e", "snapshot_date": "2026-09-08", "active_loans": 3, "outstanding_balance": 4600, "par7": 0, "par30": 0.05, "par60": 0.05, "par90": 0},
        ])
        self.datasets.rows.append({"dataset_id": "api-e2e", "source_name": "API E2E"})

    def get_dataset(self, dataset_id):
        return next((r for r in self.datasets.rows if r.get("dataset_id") == dataset_id), None)

    def list_datasets(self):
        return list(self.datasets.rows)

    def get_snapshot(self, dataset_id, snapshot_date=None):
        matches = [r for r in self.snapshots.rows if r.get("dataset_id") == dataset_id]
        if snapshot_date:
            matches = [r for r in matches if r.get("snapshot_date") == snapshot_date]
        return matches[-1] if matches else None

    def list_snapshots(self, dataset_id, limit=100):
        return [r for r in self.snapshots.rows if r.get("dataset_id") == dataset_id][-limit:]

    def save_snapshot(self, document):
        self.snapshots.rows.append(dict(document))
        return document

    def list_records(self, dataset_id, limit=100):
        return [r for r in self.records.rows if r.get("dataset_id") == dataset_id][:limit]


def test_dataset_history_endpoint_returns_snapshots(monkeypatch) -> None:
    fake = FakePersistence()
    monkeypatch.setattr(dataset_registry_routes, "persistence", fake)
    response = TestClient(app).get("/api/v1/datasets/api-e2e/history")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert [s["id"] for s in body["snapshots"]] == ["s1", "s2"]
    assert body["trend_available"] is True


def test_dataset_run_endpoint_returns_unified_contract(monkeypatch) -> None:
    fake = FakePersistence()
    monkeypatch.setattr(dataset_router, "persistence", fake)
    response = TestClient(app).post("/api/v1/datasets/api-e2e/run", json={"snapshot_date": "2026-09-09"})
    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == "dataset-intelligence-v6"
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
    fake.snapshots.rows.append({"id": "snapshot-old", "dataset_id": "api-e2e", "snapshot_date": "2026-09-08", "active_loans": 3, "outstanding_balance": 4600, "par7": 0, "par30": 0.05, "par60": 0.05, "par90": 0})
    monkeypatch.setattr(dataset_router, "persistence", fake)
    response = TestClient(app).post("/api/v1/datasets/api-e2e/run", json={"snapshot_date": "2026-09-09"})
    assert response.status_code == 200
    body = response.json()
    assert body["previous_snapshot"]["id"] == "snapshot-old"
    assert body["governance"]["trend_available"] is True
    assert body["workspace"]["decision_center"]["trend"]["status"] in {"deteriorating", "improving", "stable"}
