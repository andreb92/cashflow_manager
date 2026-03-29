from datetime import date
from dateutil.relativedelta import relativedelta
from app.services.billing import billing_month


def expand_recurrence(start_date: date, pm_type: str, n: int) -> list[dict]:
    occurrences = []
    for i in range(n):
        occ_date = start_date + relativedelta(months=i)
        occurrences.append({
            "date": occ_date,
            "billing_month": billing_month(pm_type, occ_date),
        })
    return occurrences
