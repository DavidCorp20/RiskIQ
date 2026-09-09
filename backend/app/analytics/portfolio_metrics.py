from collections.abc import Iterable
from datetime import date
from decimal import Decimal

from app.domain.models import Installment, Loan


def days_past_due(due_date: date, as_of: date, paid_amount: Decimal, scheduled_amount: Decimal) -> int:
    if paid_amount >= scheduled_amount:
        return 0
    return max((as_of - due_date).days, 0)


def loan_dpd(loan: Loan, installments: Iterable[Installment], as_of: date) -> int:
    pending = [i for i in installments if i.loan_id == loan.loan_id and i.due_date <= as_of and i.paid_amount < i.scheduled_amount]
    if not pending:
        return 0
    return max(days_past_due(i.due_date, as_of, i.paid_amount, i.scheduled_amount) for i in pending)


def par_ratio(loans: Iterable[Loan], installments: Iterable[Installment], as_of: date, threshold_days: int) -> Decimal:
    loan_list = list(loans)
    denominator = sum((loan.outstanding_principal for loan in loan_list), Decimal("0"))
    if denominator == 0:
        return Decimal("0")

    installment_list = list(installments)
    numerator = sum(
        (loan.outstanding_principal for loan in loan_list if loan_dpd(loan, installment_list, as_of) >= threshold_days),
        Decimal("0"),
    )
    return numerator / denominator


def portfolio_health(loans: Iterable[Loan], installments: Iterable[Installment], as_of: date) -> dict[str, Decimal | int]:
    loan_list = list(loans)
    installment_list = list(installments)
    return {
        "active_loans": len([loan for loan in loan_list if loan.status == "active"]),
        "outstanding_balance": sum((loan.outstanding_principal for loan in loan_list), Decimal("0")),
        "par7": par_ratio(loan_list, installment_list, as_of, 7),
        "par30": par_ratio(loan_list, installment_list, as_of, 30),
        "par60": par_ratio(loan_list, installment_list, as_of, 60),
        "par90": par_ratio(loan_list, installment_list, as_of, 90),
    }
