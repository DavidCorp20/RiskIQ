from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.data.persistence import PortfolioPersistenceService

router = APIRouter(prefix="/v1/datasets", tags=["datasets"])
persistence = PortfolioPersistenceService()


@router.get("/{dataset_id}")
def get_dataset(dataset_id: str) -> dict:
    rows = persistence.datasets.find({"dataset_id": dataset_id}, limit=1)
    if not rows:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return rows[0]


@router.get("/{dataset_id}/portfolio")
def get_dataset_portfolio(dataset_id: str) -> dict:
    if not persistence.datasets.find({"dataset_id": dataset_id}, limit=1):
        raise HTTPException(status_code=404, detail="Dataset not found")
    customers = persistence.customers.find({"dataset_id": dataset_id}, limit=100000)
    loans = persistence.loans.find({"dataset_id": dataset_id}, limit=100000)
    installments = persistence.installments.find({"dataset_id": dataset_id}, limit=100000)
    payments = persistence.payments.find({"dataset_id": dataset_id}, limit=100000)
    return {
        "dataset_id": dataset_id,
        "customers": customers,
        "loans": loans,
        "installments": installments,
        "payments": payments,
        "summary": {
            "customer_count": len(customers),
            "loan_count": len(loans),
            "installment_count": len(installments),
            "payment_count": len(payments),
        },
    }
