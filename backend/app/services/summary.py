from sqlalchemy.orm import Session
from app.models.transaction import Transaction
from app.models.transfer import Transfer
from app.models.payment_method import PaymentMethod
from app.services.bank_balance import compute_bank_balance


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

    return {
        "year": year,
        "month": month,
        "incomes": total_income,
        "outcomes_by_method": by_method,
        "transfers_out_bank": transfers_out,
        "transfers_in_bank": transfers_in,
        "bank_balance": bank_balance,
    }
