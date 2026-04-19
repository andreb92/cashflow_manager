import bisect
from collections import defaultdict
from sqlalchemy.orm import Session
from app.models.payment_method import PaymentMethod, MainBankHistory
from app.models.transaction import Transaction
from app.models.transfer import Transfer
from app.services.billing import NEXT_MONTH_TYPES


def _bulk_load(user_id: str, start_month_first: str, end_date: str, db: Session):
    """Bulk-load every dataset needed to walk the rolling bank balance.

    Returns a tuple ``(mbh_rows, mbh_dates, pm_by_id, txs_by_month, transfers_by_month)``:
    - ``mbh_rows``: MainBankHistory rows for the user, ordered by ``valid_from`` asc
    - ``mbh_dates``: parallel list of ``valid_from`` strings for O(log n) bisect lookup
    - ``pm_by_id``: ``{payment_method_id: PaymentMethod}``
    - ``txs_by_month``: ``{billing_month: [Transaction, ...]}``
    - ``transfers_by_month``: ``{billing_month: [Transfer, ...]}``
    """
    mbh_rows = (
        db.query(MainBankHistory)
        .filter_by(user_id=user_id)
        .order_by(MainBankHistory.valid_from.asc())
        .all()
    )
    pm_by_id: dict[str, PaymentMethod] = {
        pm.id: pm
        for pm in db.query(PaymentMethod).filter_by(user_id=user_id).all()
    }
    all_txs = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.billing_month >= start_month_first,
            Transaction.billing_month <= end_date,
        )
        .all()
    )
    txs_by_month: dict[str, list[Transaction]] = defaultdict(list)
    for tx in all_txs:
        txs_by_month[tx.billing_month].append(tx)

    all_transfers = (
        db.query(Transfer)
        .filter(
            Transfer.user_id == user_id,
            Transfer.billing_month >= start_month_first,
            Transfer.billing_month <= end_date,
        )
        .all()
    )
    transfers_by_month: dict[str, list[Transfer]] = defaultdict(list)
    for t in all_transfers:
        transfers_by_month[t.billing_month].append(t)

    mbh_dates = [row.valid_from for row in mbh_rows]  # already sorted asc
    return mbh_rows, mbh_dates, pm_by_id, txs_by_month, transfers_by_month


def _accumulate_balances(
    mbh_rows: list,
    mbh_dates: list[str],
    pm_by_id: dict,
    txs_by_month: dict,
    transfers_by_month: dict,
    start_year: int,
    start_month: int,
    until_year: int,
    until_month: int,
) -> dict[str, float]:
    """Walk month-by-month from (start_year, start_month) through (until_year, until_month),
    applying the main bank's opening balance, transactions, and transfers. Returns a dict
    keyed by ``'YYYY-MM-01'`` month-first string to the end-of-month rolling balance.
    """
    result: dict[str, float] = {}
    balance = 0.0
    curr_year, curr_month = start_year, start_month

    while (curr_year, curr_month) <= (until_year, until_month):
        month_first = f"{curr_year:04d}-{curr_month:02d}-01"

        # Binary search: rightmost MBH row with valid_from <= month_first
        idx = bisect.bisect_right(mbh_dates, month_first) - 1
        mbh = mbh_rows[idx] if idx >= 0 else None

        if mbh:
            # On the first month for THIS main bank entry, start from its opening_balance
            if mbh.valid_from == month_first:
                balance = float(mbh.opening_balance)

            pm = pm_by_id.get(mbh.payment_method_id)
            if pm:
                # Apply transactions for this billing month
                for tx in txs_by_month.get(month_first, []):
                    if tx.payment_method_id == pm.id:
                        # Transactions directly on the main bank PM
                        if tx.transaction_direction == "income":
                            balance += float(tx.amount)
                        else:
                            balance -= float(tx.amount)
                    elif tx.transaction_direction == "credit":
                        # Revolving/credit-card payoff recorded as "credit".
                        # Prepaid, saving, or other PMs are not bank-funded.
                        tx_pm = pm_by_id.get(tx.payment_method_id)
                        if tx_pm and tx_pm.type in NEXT_MONTH_TYPES:
                            balance -= float(tx.amount)
                    elif tx.transaction_direction == "debit":
                        # Credit card purchases shift to billing_month (next month).
                        # Deduct them from the bank balance in that billing month so the
                        # balance reflects the upcoming CC bill.
                        tx_pm = pm_by_id.get(tx.payment_method_id)
                        if tx_pm and tx_pm.type == "credit_card":
                            balance -= float(tx.amount)

                # Apply transfers for this billing month — prefer the stable FK id
                # when available, fall back to name matching for legacy rows that
                # predate the 008 migration / FK backfill.
                for t in transfers_by_month.get(month_first, []):
                    from_match = (
                        (t.from_payment_method_id is not None and t.from_payment_method_id == pm.id)
                        or (t.from_payment_method_id is None and t.from_account_name == pm.name)
                    )
                    to_match = (
                        (t.to_payment_method_id is not None and t.to_payment_method_id == pm.id)
                        or (t.to_payment_method_id is None and t.to_account_name == pm.name)
                    )
                    if from_match:
                        balance -= float(t.amount)
                    elif to_match:
                        balance += float(t.amount)

        result[month_first] = balance
        curr_year, curr_month = _advance_month(curr_year, curr_month)

    return result


def compute_bank_balance(
    user_id: str,
    year: int,
    month: int,
    db: Session,
    *,
    _preloaded: dict | None = None,
) -> float:
    """
    Compute rolling bank balance for the given year/month.
    Starts from tracking_start_date's main bank opening_balance and applies
    income/debit transactions and transfers month by month up to and including
    the requested month.

    When ``_preloaded`` is provided (a dict with keys ``mbh_rows``, ``mbh_dates``,
    ``pm_by_id``, ``txs_by_month``, ``transfers_by_month``, ``start_year``,
    ``start_month``), the bulk queries are skipped and the supplied data is used —
    this lets callers such as :func:`app.services.summary.monthly_summary` load the
    datasets once and reuse them.
    """
    from app.models.user import UserSetting

    if _preloaded is not None:
        start_year = _preloaded["start_year"]
        start_month = _preloaded["start_month"]
        mbh_rows = _preloaded["mbh_rows"]
        mbh_dates = _preloaded["mbh_dates"]
        pm_by_id = _preloaded["pm_by_id"]
        txs_by_month = _preloaded["txs_by_month"]
        transfers_by_month = _preloaded["transfers_by_month"]
    else:
        start_setting = db.query(UserSetting).filter_by(user_id=user_id, key="tracking_start_date").first()
        if not start_setting:
            return 0.0
        start_parts = start_setting.value.split("-")
        start_year, start_month = int(start_parts[0]), int(start_parts[1])

        start_month_first = f"{start_year:04d}-{start_month:02d}-01"
        end_date = f"{year:04d}-{month:02d}-01"
        mbh_rows, mbh_dates, pm_by_id, txs_by_month, transfers_by_month = _bulk_load(
            user_id, start_month_first, end_date, db
        )

    if not mbh_rows:
        return 0.0

    balances = _accumulate_balances(
        mbh_rows, mbh_dates, pm_by_id, txs_by_month, transfers_by_month,
        start_year, start_month, year, month,
    )

    target_key = f"{year:04d}-{month:02d}-01"
    return balances.get(target_key, 0.0)


def compute_bank_balances_for_year(user_id: str, year: int, db: Session) -> dict[int, float]:
    """
    Compute the bank balance at end of each month for a full year in a single pass.
    Does the same 4 bulk loads as compute_bank_balance but only once, then accumulates
    from tracking_start through December, capturing the balance at each month boundary.
    Returns {1: balance, 2: balance, ..., 12: balance}.
    """
    from app.models.user import UserSetting
    start_setting = db.query(UserSetting).filter_by(user_id=user_id, key="tracking_start_date").first()
    if not start_setting:
        return {m: 0.0 for m in range(1, 13)}
    start_parts = start_setting.value.split("-")
    start_year, start_month = int(start_parts[0]), int(start_parts[1])

    start_month_first = f"{start_year:04d}-{start_month:02d}-01"
    end_date = f"{year:04d}-12-01"

    mbh_rows, mbh_dates, pm_by_id, txs_by_month, transfers_by_month = _bulk_load(
        user_id, start_month_first, end_date, db
    )

    balances = _accumulate_balances(
        mbh_rows, mbh_dates, pm_by_id, txs_by_month, transfers_by_month,
        start_year, start_month, year, 12,
    )

    result: dict[int, float] = {}
    for m in range(1, 13):
        key = f"{year:04d}-{m:02d}-01"
        result[m] = balances.get(key, 0.0)
    return result


def _advance_month(year: int, month: int):
    if month == 12:
        return year + 1, 1
    return year, month + 1
