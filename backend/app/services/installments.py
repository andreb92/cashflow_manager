from datetime import date
from dateutil.relativedelta import relativedelta


def expand_installments(amount: float, transaction_date: date, n: int) -> list[dict]:
    base_amount = round(amount / n, 2)
    installments = []
    for i in range(n):
        billing = (transaction_date.replace(day=1) + relativedelta(months=i + 1))
        inst_amount = base_amount if i < n - 1 else round(amount - base_amount * (n - 1), 2)
        installments.append({
            "amount": inst_amount,
            "billing_month": billing,
            "installment_index": i + 1,
            "installment_total": n,
        })
    return installments
