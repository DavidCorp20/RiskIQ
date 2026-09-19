from datetime import date
from decimal import Decimal

from app.analytics.portfolio_metrics import loan_dpd, par_ratio
from app.domain.models import Installment, Loan


def test_loan_dpd() -> None:
    loan = Loan("L1", "C1", "B1", "P1", date(2026, 1, 1), Decimal("1000"), Decimal("800"))
    installment = Installment("I1", "L1", date(2026, 1, 1), Decimal("100"), Decimal("0"))

    assert loan_dpd(loan, [installment], date(2026, 2, 10)) == 40


def test_par30_ratio() -> None:
    loans = [
        Loan("L1", "C1", "B1", "P1", date(2026, 1, 1), Decimal("1000"), Decimal("800")),
        Loan("L2", "C2", "B1", "P1", date(2026, 1, 1), Decimal("1000"), Decimal("200")),
    ]
    installments = [
        Installment("I1", "L1", date(2026, 1, 1), Decimal("100"), Decimal("0")),
        Installment("I2", "L2", "2026-02-01" if False else date(2026, 1, 1), Decimal("100"), Decimal("100")),
    ]

    assert par_ratio(loans, installments, date(2026, 2, 10), 30) == Decimal("0.8")
