from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.transaction import Transaction
from app.models.category import Category
from app.models.transfer import Transfer


def category_spending(
    user_id: str,
    from_ym: str,
    to_ym: str,
    db: Session,
    category_ids: Optional[List[str]] = None,
    payment_method_ids: Optional[List[str]] = None,
    direction: str = "all",
) -> list:
    # billing_month is stored as "YYYY-MM-DD" (first day of month);
    # from_ym/to_ym arrive as "YYYY-MM"
    from_date = from_ym[:7] + "-01"
    to_date = to_ym[:7] + "-01"

    q = (
        db.query(
            Transaction.category_id,
            Transaction.billing_month,
            func.sum(Transaction.amount).label("total_amount"),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.billing_month >= from_date,
            Transaction.billing_month <= to_date,
        )
    )
    if direction != "all":
        q = q.filter(Transaction.transaction_direction == direction)
    if category_ids:
        q = q.filter(Transaction.category_id.in_(category_ids))
    if payment_method_ids:
        q = q.filter(Transaction.payment_method_id.in_(payment_method_ids))

    rows = q.group_by(Transaction.category_id, Transaction.billing_month).all()

    if not rows:
        return []

    cat_ids = {r.category_id for r in rows if r.category_id}
    cats = {c.id: c for c in db.query(Category).filter(Category.id.in_(cat_ids)).all()}

    result = []
    for row in rows:
        cat = cats.get(row.category_id)
        result.append({
            "category_id": row.category_id,
            "type": cat.type if cat else None,
            "sub_type": cat.sub_type if cat else None,
            "month": row.billing_month[:7],
            "total_amount": round(float(row.total_amount), 2),
        })
    return result


def transfer_spending(user_id: str, from_ym: str, to_ym: str, db: Session) -> list:
    """Aggregate transfers to saving/investment/pension accounts by month."""
    from_date = from_ym[:7] + "-01"
    to_date = to_ym[:7] + "-01"

    rows = (
        db.query(
            Transfer.to_account_type,
            Transfer.to_account_name,
            Transfer.billing_month,
            func.sum(Transfer.amount).label("total_amount"),
        )
        .filter(
            Transfer.user_id == user_id,
            Transfer.billing_month >= from_date,
            Transfer.billing_month <= to_date,
            Transfer.to_account_type.in_(["saving", "investment", "pension"]),
        )
        .group_by(Transfer.to_account_type, Transfer.to_account_name, Transfer.billing_month)
        .all()
    )

    return [
        {
            "to_account_type": r.to_account_type,
            "to_account_name": r.to_account_name,
            "month": r.billing_month[:7],
            "total_amount": round(float(r.total_amount), 2),
        }
        for r in rows
    ]
