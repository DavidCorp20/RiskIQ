from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.data.persistence import PortfolioPersistenceService

router = APIRouter(prefix="/v1/datasets", tags=["datasets"])
persistence = PortfolioPersistenceService()


def _require_dataset(dataset_id: str) -> dict:
    rows = persistence.datasets.find({"dataset_id": dataset_id}, limit=1)
    if not rows:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return rows[0]


@router.get("")
def list_datasets() -> dict:
    """Return persisted datasets ordered newest-first for workspace restoration."""
    rows = persistence.datasets.find({}, limit=1000)
    rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    latest: dict[str, dict] = {}
    for row in rows:
        dataset_id = str(row.get("dataset_id") or "")
        if dataset_id and dataset_id not in latest:
            latest[dataset_id] = row
    return {"count": len(latest), "datasets": list(latest.values())}


@router.get("/{dataset_id}")
def get_dataset(dataset_id: str) -> dict:
    return _require_dataset(dataset_id)


@router.get("/{dataset_id}/history")
def get_dataset_history(dataset_id: str) -> dict:
    """Return chronological snapshots for portfolio trend and audit views."""
    _require_dataset(dataset_id)
    rows = persistence.snapshots.find({"dataset_id": dataset_id}, limit=1000)
    rows.sort(key=lambda row: str(row.get("snapshot_date") or ""))
    return {
        "dataset_id": dataset_id,
        "count": len(rows),
        "snapshots": rows,
        "trend_available": len(rows) >= 2,
    }


@router.get("/{dataset_id}/portfolio")
def get_dataset_portfolio(dataset_id: str) -> dict:
    _require_dataset(dataset_id)
    customers = persistence.customers.find({"dataset_id": dataset_id}, limit=100000)
    loans = persistence.loans.find({"dataset_id": dataset_id}, limit=100000)
    installments = persistence.installments.find({"dataset_id": dataset_id}, limit=100000)
    payments = persistence.payments.find({"dataset_id": dataset_id}, limit=100000)
    return {"dataset_id":dataset_id,"customers":customers,"loans":loans,"installments":installments,"payments":payments,"summary":{"customer_count":len(customers),"loan_count":len(loans),"installment_count":len(installments),"payment_count":len(payments)}}


@router.get("/{dataset_id}/records")
def get_dataset_records(dataset_id: str) -> dict:
    _require_dataset(dataset_id)
    records = persistence.portfolio_records.find({"dataset_id": dataset_id}, limit=100000)
    return {"dataset_id":dataset_id,"count":len(records),"records":records}
