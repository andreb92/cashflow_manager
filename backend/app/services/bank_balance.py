import bisect
from collections import defaultdict
from sqlalchemy.orm import Session
from app.models.payment_method import PaymentMethod, MainBankHistory
from app.models.transaction import Transaction
from app.models.transfer import Transfer
from app.services.billing import NEXT_MONTH_TYPES


def compute_bank_balance(user_id: str, year: int, month: int, db: Session) -> float:
    """
    Compute rolling bank balance for the given year/month.
    Starts from tracking_start_date's main bank opening_balance and applies
    income/debit transactions and transfers month by month up to and including
    the requested month.

    Bulk-loads all required data before the loop to avoid N+1 queries.
    """
    from app.models.user import UserSetting
    start_setting = db.query(UserSetting).filter_by(user_id=user_id, key="tracking_start_date").first()
    if not start_setting:
        return 0.0
    start_parts = start_setting.value.split("-")
    start_year, start_month = int(start_parts[0]), int(start_parts[1])

    # --- Bulk load 1: all MainBankHistory rows, sorted by valid_from ascending ---
    mbh_rows = (
        db.query(MainBankHistory)
        .filter_by(user_id=user_id)
        .order_by(MainBankHistory.valid_from.asc())
        .all()
    )

    # --- Bulk load 2: all PaymentMethod rows for the user, keyed by id ---
    pm_by_id: dict[str, PaymentMethod] = {
        pm.id: pm
        for pm in db.query(PaymentMethod).filter_by(user_id=user_id).all()
    }

    # --- Compute date range strings for bulk queries ---
    start_month_first = f"{start_year:04d}-{start_month:02d}-01"
    end_date = f"{year:04d}-{month:02d}-01"

    # --- Bulk load 3: all Transactions in range, grouped by billing_month ---
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

    # --- Bulk load 4: all Transfers in range, grouped by billing_month ---
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

    # Pre-compute sorted valid_from list for O(log n) MBH lookup per month
    mbh_dates = [row.valid_from for row in mbh_rows]  # already sorted asc

    # --- Accumulation loop ---
    balance = 0.0
    curr_year, curr_month = start_year, start_month

    while (curr_year, curr_month) <= (year, month):
        month_first = f"{curr_year:04d}-{curr_month:02d}-01"

        # Binary search: find rightmost MBH row with valid_from <= month_first
        idx = bisect.bisect_right(mbh_dates, month_first) - 1
        mbh = mbh_rows[idx] if idx >= 0 else None

        if not mbh:
            curr_year, curr_month = _advance_month(curr_year, curr_month)
            continue

        # On the first month for THIS main bank entry, start from its opening_balance
        if mbh.valid_from == month_first:
            balance = float(mbh.opening_balance)

        pm = pm_by_id.get(mbh.payment_method_id)
        if not pm:
            curr_year, curr_month = _advance_month(curr_year, curr_month)
            continue

        # Apply transactions for this billing month
        for tx in txs_by_month.get(month_first, []):
            if tx.payment_method_id == pm.id:
                # Transactions on the main bank PM
                if tx.transaction_direction == "income":
                    balance += float(tx.amount)
                else:
                    balance -= float(tx.amount)
            elif tx.transaction_direction == "credit":
                # Revolving card payoff recorded as a "credit" direction transaction.
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

        # Apply transfers for this billing month
        for t in transfers_by_month.get(month_first, []):
            if t.from_account_name == pm.name:
                balance -= float(t.amount)
            elif t.to_account_name == pm.name:
                balance += float(t.amount)

        curr_year, curr_month = _advance_month(curr_year, curr_month)

    return balance


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

    mbh_dates = [row.valid_from for row in mbh_rows]

    balance = 0.0
    curr_year, curr_month = start_year, start_month
    result: dict[int, float] = {}

    while (curr_year, curr_month) <= (year, 12):
        month_first = f"{curr_year:04d}-{curr_month:02d}-01"

        idx = bisect.bisect_right(mbh_dates, month_first) - 1
        mbh = mbh_rows[idx] if idx >= 0 else None

        if mbh:
            if mbh.valid_from == month_first:
                balance = float(mbh.opening_balance)
            pm = pm_by_id.get(mbh.payment_method_id)
            if pm:
                for tx in txs_by_month.get(month_first, []):
                    if tx.payment_method_id == pm.id:
                        if tx.transaction_direction == "income":
                            balance += float(tx.amount)
                        else:
                            balance -= float(tx.amount)
                    elif tx.transaction_direction == "credit":
                        tx_pm = pm_by_id.get(tx.payment_method_id)
                        if tx_pm and tx_pm.type in NEXT_MONTH_TYPES:
                            balance -= float(tx.amount)
                    elif tx.transaction_direction == "debit":
                        tx_pm = pm_by_id.get(tx.payment_method_id)
                        if tx_pm and tx_pm.type == "credit_card":
                            balance -= float(tx.amount)
                for t in transfers_by_month.get(month_first, []):
                    if t.from_account_name == pm.name:
                        balance -= float(t.amount)
                    elif t.to_account_name == pm.name:
                        balance += float(t.amount)

        if curr_year == year:
            result[curr_month] = balance

        curr_year, curr_month = _advance_month(curr_year, curr_month)

    for m in range(1, 13):
        result.setdefault(m, 0.0)

    return result


def _advance_month(year: int, month: int):
    if month == 12:
        return year + 1, 1
    return year, month + 1
