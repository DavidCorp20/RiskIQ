from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class Customer:
    customer_id: str
    business_id: str
    segment: Optional[str] = None


@dataclass(frozen=True)
class Loan:
    loan_id: str
    customer_id: str
    business_id: str
    product_id: Optional[str]
    origination_date: date
    principal: Decimal
    outstanding_principal: Decimal
    status: str = "active"


@dataclass(frozen=True)
class Installment:
    installment_id: str
    loan_id: str
    due_date: date
    scheduled_amount: Decimal
    paid_amount: Decimal = Decimal("0")


@dataclass(frozen=True)
class Payment:
    payment_id: str
    loan_id: str
    payment_date: date
    amount: Decimal


@dataclass(frozen=True)
class PortfolioSnapshot:
    snapshot_date: date
    business_id: str
    outstanding_balance: Decimal
    par30_balance: Decimal
    par90_balance: Decimal
    active_loans: int
