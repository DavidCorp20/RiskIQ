from __future__ import annotations

import pytest

import app.api.ai_routes as ai_routes
import app.api.simulation_routes as simulation_routes


class FakeCollection:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    def find(self, query=None, limit=None):
        query = query or {}
        rows = [row for row in self.rows if all(row.get(k) == v for k, v in query.items())]
        return rows[:limit] if limit else rows


class FakePersistence:
    def __init__(self):
        self.datasets = FakeCollection([{"dataset_id": "ds-1", "source_name": "portfolio.csv"}])
        self.snapshots = FakeCollection([
            {"dataset_id": "ds-1", "snapshot_date": "2026-09-10", "outstanding_balance": 100000, "par30": 0.10, "par90": 0.03},
            {"dataset_id": "ds-1", "snapshot_date": "2026-09-01", "outstanding_balance": 95000, "par30": 0.08, "par90": 0.02},
        ])


def test_simulator_uses_persisted_dataset_snapshot(monkeypatch):
    monkeypatch.setattr(simulation_routes, "persistence", FakePersistence())
    result = simulation_routes.run_scenario({
        "dataset_id": "ds-1",
        "portfolio": {"balance": 1, "par30": 0, "par90": 0},
        "changes": {"collection_effectiveness_pct": 0.10},
    })
    assert result["dataset_id"] == "ds-1"
    assert result["baseline_source"] == "persisted_snapshot"
    assert result["snapshot_date"] == "2026-09-10"
    assert result["baseline"]["balance"] == 100000
    assert result["baseline"]["par30"] == 0.10


def test_simulator_rejects_dataset_without_snapshot(monkeypatch):
    fake = FakePersistence()
    fake.snapshots = FakeCollection([])
    monkeypatch.setattr(simulation_routes, "persistence", fake)
    with pytest.raises(Exception) as exc:
        simulation_routes.run_scenario({"dataset_id": "ds-1", "changes": {}})
    assert "Run the selected dataset" in str(exc.value)


def test_copilot_requires_real_dataset(monkeypatch):
    monkeypatch.setattr(ai_routes, "persistence", FakePersistence())
    result = ai_routes.copilot({
        "dataset_id": "ds-1",
        "question": "¿Qué está pasando?",
        "risk_facts": {"dataset_id": "ds-1", "facts": [], "alerts": [], "summary": {}},
    })
    assert result["dataset_id"] == "ds-1"
    assert result["grounding"]["dataset_bound"] is True
    assert result["grounding"]["customer_actions_executed"] is False


def test_copilot_rejects_cross_dataset_context(monkeypatch):
    monkeypatch.setattr(ai_routes, "persistence", FakePersistence())
    with pytest.raises(Exception) as exc:
        ai_routes.copilot({
            "dataset_id": "ds-1",
            "question": "¿Qué pasó?",
            "risk_facts": {"dataset_id": "other", "facts": [], "alerts": [], "summary": {}},
        })
    assert "does not match" in str(exc.value)
