from __future__ import annotations

import random
from datetime import date, timedelta

from app.data.persistence import PortfolioPersistenceService


BUSINESS_ID = "riskiq-demo"


def build_demo() -> dict[str, list[dict]]:
    random.seed(42)
    customers = []
    loans = []
    installments = []
    payments = []

    for index in range(1, 101):
        customer_id = f"C{index:04d}"
        loan_id = f"L{index:04d}"
        segment = ["A", "B", "C"][index % 3]
        principal = float(random.choice([500, 750, 1000, 1500, 2000]))
        origination = date(2026, 1, 1) + timedelta(days=index % 180)
        customers.append({"customer_id": customer_id, "business_id": BUSINESS_ID, "segment": segment})
        loans.append({
            "loan_id": loan_id,
            "customer_id": customer_id,
            "business_id": BUSINESS_ID,
            "product_id": "PERSONAL",
            "origination_date": origination.isoformat(),
            "principal": principal,
            "outstanding_principal": principal * 0.8,
            "status": "active",
            "dpd": [0, 5, 12, 35, 75, 110][index % 6],
        })
        due = date(2026, 8, 1) + timedelta(days=index % 15)
        scheduled = principal / 6
        dpd = loans[-1]["dpd"]
        paid = 0.0 if dpd >= 35 else scheduled
        installments.append({
            "installment_id": f"I{index:04d}",
            "loan_id": loan_id,
            "business_id": BUSINESS_ID,
            "due_date": due.isoformat(),
            "scheduled_amount": scheduled,
            "paid_amount": paid,
        })
        payments.append({
            "payment_id": f"P{index:04d}",
            "loan_id": loan_id,
            "business_id": BUSINESS_ID,
            "payment_date": (due - timedelta(days=2)).isoformat(),
            "amount": paid,
        })

    return {
        "customers": customers,
        "loans": loans,
        "installments": installments,
        "payments": payments,
        "portfolio_snapshots": [
            {
                "business_id": BUSINESS_ID,
                "snapshot_date": "2026-08-31",
                "source": "seed_demo",
            }
        ],
    }


def main() -> None:
    persistence = PortfolioPersistenceService()
    demo = build_demo()
    for collection, rows in demo.items():
        persistence.save_batch(collection, rows)
        print(f"{collection}: {len(rows)}")


if __name__ == "__main__":
    main()
