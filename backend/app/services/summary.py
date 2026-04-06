from sqlalchemy.orm import Session
from app.models.transaction import Transaction
from app.models.transfer import Transfer
from app.models.payment_method import PaymentMethod
from app.services.bank_balance import compute_bank_balance, compute_bank_balances_for_year


_STAMP_DUTY_THRESHOLD = 77.47
_STAMP_DUTY_AMOUNT = 2.00


def _compute_stamp_duty(user_id: str, month_first: str, all_txs: list, db: Session) -> float:
    """
    Compute the Italian imposta di bollo (stamp duty) for a given month.

    Rules:
    - Only credit cards with has_stamp_duty == True are eligible.
    - If monthly spend on such a card exceeds €77.47, add €2.00 per card.
    """
    stamp_duty_cards = (
        db.query(PaymentMethod)
        .filter_by(user_id=user_id, type="credit_card", has_stamp_duty=True)
        .all()
    )
    if not stamp_duty_cards:
        return 0.0

    total = 0.0
    for pm in stamp_duty_cards:
        monthly_spend = sum(
            float(tx.amount)
            for tx in all_txs
            if tx.payment_method_id == pm.id
            and tx.billing_month == month_first
            and tx.transaction_direction in ("debit", "credit")
        )
        if monthly_spend > _STAMP_DUTY_THRESHOLD:
            total += _STAMP_DUTY_AMOUNT

    return total


def monthly_summary(user_id: str, year: int, month: int, db: Session) -> dict:
    month_first = f"{year:04d}-{month:02d}-01"

    txs = db.query(Transaction).filter_by(user_id=user_id).filter(
        Transaction.billing_month == month_first
    ).all()

    total_income = sum(float(t.amount) for t in txs if t.transaction_direction == "income")

    # Build outcomes keyed by payment method name
    pm_ids = {t.payment_method_id for t in txs if t.transaction_direction in ("debit", "credit")}
    pm_names: dict[str, str] = {}
    if pm_ids:
        pms = db.query(PaymentMethod).filter(PaymentMethod.id.in_(pm_ids)).all()
        pm_names = {pm.id: pm.name for pm in pms}

    by_method: dict[str, float] = {}
    for tx in txs:
        if tx.transaction_direction in ("debit", "credit"):
            name = pm_names.get(tx.payment_method_id, tx.payment_method_id)
            by_method[name] = by_method.get(name, 0) + float(tx.amount)

    # Transfers affecting bank balance
    transfers = db.query(Transfer).filter_by(user_id=user_id).filter(
        Transfer.billing_month == month_first
    ).all()

    transfers_out = sum(float(t.amount) for t in transfers if t.from_account_type == "bank")
    transfers_in = sum(float(t.amount) for t in transfers if t.to_account_type == "bank")

    bank_balance = compute_bank_balance(user_id, year, month, db)

    stamp_duty = _compute_stamp_duty(user_id, month_first, txs, db)

    return {
        "year": year,
        "month": month,
        "incomes": total_income,
        "outcomes_by_method": by_method,
        "transfers_out_bank": transfers_out,
        "transfers_in_bank": transfers_in,
        "bank_balance": bank_balance,
        "stamp_duty": stamp_duty,
    }


def year_monthly_summaries(user_id: str, year: int, db: Session) -> list[dict]:
    """
    Compute all 12 monthly summaries for a year in a single pass.
    Uses compute_bank_balances_for_year to avoid re-loading all history 12 times.
    Total DB queries: ~7 regardless of history length (vs 72 with 12x monthly_summary calls).
    """
    year_prefix = f"{year:04d}-"

    # Load all transactions for the year in one query
    all_txs = (
        db.query(Transaction)
        .filter_by(user_id=user_id)
        .filter(Transaction.billing_month.startswith(year_prefix))
        .all()
    )
    txs_by_month: dict[int, list[Transaction]] = {m: [] for m in range(1, 13)}
    for tx in all_txs:
        m = int(tx.billing_month[5:7])
        txs_by_month[m].append(tx)

    # Load all PMs referenced by this year's transactions in one query
    pm_ids = {tx.payment_method_id for tx in all_txs}
    pm_names: dict[str, str] = {}
    if pm_ids:
        pms = db.query(PaymentMethod).filter(PaymentMethod.id.in_(pm_ids)).all()
        pm_names = {pm.id: pm.name for pm in pms}

    # Load all transfers for the year in one query
    all_transfers = (
        db.query(Transfer)
        .filter_by(user_id=user_id)
        .filter(Transfer.billing_month.startswith(year_prefix))
        .all()
    )
    transfers_by_month: dict[int, list[Transfer]] = {m: [] for m in range(1, 13)}
    for t in all_transfers:
        m = int(t.billing_month[5:7])
        transfers_by_month[m].append(t)

    # Single-pass bank balance computation for all 12 months
    bank_balances = compute_bank_balances_for_year(user_id, year, db)

    # Load stamp-duty credit cards once for the whole year
    stamp_duty_cards = (
        db.query(PaymentMethod)
        .filter_by(user_id=user_id, type="credit_card", has_stamp_duty=True)
        .all()
    )

    results = []
    for month in range(1, 13):
        txs = txs_by_month[month]
        total_income = sum(float(t.amount) for t in txs if t.transaction_direction == "income")

        by_method: dict[str, float] = {}
        for tx in txs:
            if tx.transaction_direction in ("debit", "credit"):
                name = pm_names.get(tx.payment_method_id, tx.payment_method_id)
                by_method[name] = by_method.get(name, 0) + float(tx.amount)

        transfers = transfers_by_month[month]
        transfers_out = sum(float(t.amount) for t in transfers if t.from_account_type == "bank")
        transfers_in = sum(float(t.amount) for t in transfers if t.to_account_type == "bank")

        month_first = f"{year:04d}-{month:02d}-01"
        stamp_duty = 0.0
        for pm in stamp_duty_cards:
            monthly_spend = sum(
                float(tx.amount)
                for tx in txs
                if tx.payment_method_id == pm.id
                and tx.transaction_direction in ("debit", "credit")
            )
            if monthly_spend > _STAMP_DUTY_THRESHOLD:
                stamp_duty += _STAMP_DUTY_AMOUNT

        results.append({
            "year": year,
            "month": month,
            "incomes": total_income,
            "outcomes_by_method": by_method,
            "transfers_out_bank": transfers_out,
            "transfers_in_bank": transfers_in,
            "bank_balance": bank_balances[month],
            "stamp_duty": stamp_duty,
        })

    return results
