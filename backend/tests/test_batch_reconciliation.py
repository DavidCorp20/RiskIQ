import pytest

from app.api import data_routes


class FakeRepository:
    def __init__(self, rows):
        self.rows = rows

    def find(self, *_args, **_kwargs):
        return [dict(row) for row in self.rows]

    def insert(self, row):
        self.rows.append(dict(row))

    def update(self, selector, update):
        for row in self.rows:
            if all(row.get(k) == v for k, v in selector.items()):
                row.update(update.get("$set", {}))
                return
        raise AssertionError("row not found")


class FakePersistence:
    def __init__(self, rows):
        self.portfolio_records = FakeRepository(rows)
        self.saved_projection = None

    def save_normalized_portfolio(self, rows, dataset_id, source_name, quality_result=None):
        for row in rows:
            self.portfolio_records.insert({**row, "dataset_id": dataset_id, "source_name": source_name})
        return len(rows)

    def reconcile_update(self, existing, incoming, dataset_id, source_name, force=False):
        merged = dict(incoming) if force else dict(existing)
        if not force:
            for key, value in incoming.items():
                if merged.get(key) in (None, "") and value not in (None, ""):
                    merged[key] = value
        merged.update({"dataset_id": dataset_id, "source_name": source_name})
        self.portfolio_records.update(
            {"dataset_id": dataset_id, "loan_id": existing["loan_id"], "snapshot_date": existing["snapshot_date"]},
            {"$set": merged},
        )
        return merged

    def save_projection(self, portfolio, dataset_id):
        self.saved_projection = portfolio
        return {"loans": len(portfolio.get("loans", []))}


class FakeAudit:
    def __init__(self):
        self.entries = []

    def record(self, **entry):
        self.entries.append(entry)
        return entry


class FakeProjection:
    @staticmethod
    def project(rows):
        return {"summary": {"snapshot_date": max((r.get("snapshot_date", "") for r in rows), default="")}, "loans": rows}


def row(**changes):
    base = {"loan_id": "CR-1", "snapshot_date": "2025-01-01", "outstanding_principal": 1000, "dpd": 5, "status": "active", "paid_amount": 100, "scheduled_amount": 200}
    base.update(changes)
    return base


def test_batch_override_requires_global_justification():
    with pytest.raises(Exception) as exc:
        data_routes.batch_override_conflicts({"dataset_id": "ds", "conflict_ids": ["CR-1|2025-01-01"]})
    assert getattr(exc.value, "status_code", None) == 400


def test_batch_override_rechecks_conflict_and_audits_each_transaction(monkeypatch):
    existing = {**row(), "dataset_id": "ds"}
    persistence = FakePersistence([existing])
    audit = FakeAudit()
    monkeypatch.setattr(data_routes, "persistence", persistence)
    monkeypatch.setattr(data_routes, "audit", audit)
    monkeypatch.setattr(data_routes, "projection", FakeProjection())

    incoming = row(dpd=35, status="delinquent")
    key = "CR-1|2025-01-01"
    result = data_routes.batch_override_conflicts({
        "dataset_id": "ds",
        "conflict_ids": [key],
        "incoming_by_key": {key: incoming},
        "pending_items": [{"key": key, "classification": "conflict", "incoming": incoming}],
        "justification": "Fuente oficial corrigió el cierre.",
        "actor": "analyst",
    })

    assert result["status"] == "batch_override_applied"
    assert result["updated"] == 1
    assert len(audit.entries) == 2
    assert {entry["operation"] for entry in audit.entries} == {"conflict", "updated"}
    assert all(entry["reason"] == "Fuente oficial corrigió el cierre." for entry in audit.entries)
    assert persistence.portfolio_records.rows[0]["dpd"] == 35


def test_batch_override_rejects_stale_non_conflict(monkeypatch):
    existing = {**row(dpd=35), "dataset_id": "ds"}
    persistence = FakePersistence([existing])
    monkeypatch.setattr(data_routes, "persistence", persistence)
    monkeypatch.setattr(data_routes, "audit", FakeAudit())

    incoming = row(dpd=35)
    key = "CR-1|2025-01-01"
    with pytest.raises(Exception) as exc:
        data_routes.batch_override_conflicts({
            "dataset_id": "ds",
            "conflict_ids": [key],
            "incoming_by_key": {key: incoming},
            "pending_items": [{"key": key, "classification": "conflict", "incoming": incoming}],
            "justification": "Revisión de fuente.",
        })
    assert getattr(exc.value, "status_code", None) == 409
