from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Literal
from app.deps import get_db, get_current_user
from app.models.user import User
from app.models.transaction import Transaction
from app.models.payment_method import PaymentMethod
from app.models.category import Category
from app.schemas.transaction import TransactionCreate, TransactionUpdate
from app.services.billing import billing_month
from app.services.recurrence import expand_recurrence
from decimal import Decimal
from dateutil.parser import parse as parse_date

router = APIRouter(prefix="/transactions", tags=["transactions"])

def _get_pm(db, pm_id, user_id):
    pm = db.query(PaymentMethod).filter_by(id=pm_id, user_id=user_id).first()
    if not pm:
        raise HTTPException(422, "payment_method_id not found")
    return pm


def _ensure_category_owned_by_user(db, category_id, user_id):
    if category_id is None:
        return None
    category = db.query(Category).filter_by(id=category_id, user_id=user_id).first()
    if not category:
        raise HTTPException(422, "category_id not found")
    return category


def _promote_transaction_series_root_if_needed(db: Session, user_id: str, tx: Transaction) -> None:
    """When deleting a recurring root as single, promote the next row to root.

    Without this, deleting the root can violate the self-FK because children still
    reference the deleted id.
    """
    if tx.parent_transaction_id is not None:
        return

    children = (
        db.query(Transaction)
        .filter_by(user_id=user_id, parent_transaction_id=tx.id)
        .order_by(Transaction.date.asc(), Transaction.created_at.asc(), Transaction.id.asc())
        .all()
    )
    if not children:
        return

    new_root = children[0]
    new_root.parent_transaction_id = None
    for child in children[1:]:
        child.parent_transaction_id = new_root.id

@router.get("")
def list_transactions(
    billing_month: Optional[str] = Query(None),  # YYYY-MM — used by dashboard/summary
    date_month: Optional[str] = Query(None),     # YYYY-MM — used by transactions page (filters by actual date)
    payment_method_id: Optional[str] = None,
    parent_id: Optional[str] = None,
    limit: Optional[int] = Query(None),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if billing_month is None and date_month is None and limit is None:
        raise HTTPException(400, "At least one of billing_month, date_month, or limit is required")
    q = db.query(Transaction).filter_by(user_id=current_user.id)
    if billing_month:
        q = q.filter(Transaction.billing_month.startswith(billing_month))
    if date_month:
        q = q.filter(Transaction.date.startswith(date_month))
    if payment_method_id:
        q = q.filter_by(payment_method_id=payment_method_id)
    if parent_id:
        q = q.filter_by(parent_transaction_id=parent_id)
    q = q.order_by(Transaction.date.asc(), Transaction.created_at.asc(), Transaction.id.asc())
    q = q.offset(offset)
    if limit is not None:
        q = q.limit(limit)
    return q.all()

@router.post("")
def create_transaction(
    req: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pm = _get_pm(db, req.payment_method_id, current_user.id)
    _ensure_category_owned_by_user(db, req.category_id, current_user.id)

    if req.recurrence_months:
        tx_date = parse_date(req.date).date()
        occurrences = expand_recurrence(tx_date, pm.type, req.recurrence_months)
        first = None
        for i, occ in enumerate(occurrences):
            tx = Transaction(
                user_id=current_user.id, date=str(occ["date"]), detail=req.detail,
                amount=req.amount, payment_method_id=req.payment_method_id,
                category_id=req.category_id, transaction_direction=req.transaction_direction,
                billing_month=str(occ["billing_month"]),
                recurrence_months=req.recurrence_months, notes=req.notes,
            )
            db.add(tx)
            db.flush()
            if i == 0:
                first = tx
            else:
                tx.parent_transaction_id = first.id
        db.commit()
        db.refresh(first)
        return first

    # Single transaction
    tx_date = parse_date(req.date).date()
    bm = billing_month(pm.type, tx_date)
    tx = Transaction(
        user_id=current_user.id, date=req.date, detail=req.detail,
        amount=req.amount, payment_method_id=req.payment_method_id,
        category_id=req.category_id, transaction_direction=req.transaction_direction,
        billing_month=str(bm), notes=req.notes,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx

@router.get("/{tx_id}")
def get_transaction(tx_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter_by(id=tx_id, user_id=current_user.id).first()
    if not tx:
        raise HTTPException(404, "Not found")
    return tx

@router.put("/{tx_id}")
def update_transaction(
    tx_id: str, req: TransactionUpdate,
    cascade: Literal["single", "future", "all"] = Query("single"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tx = db.query(Transaction).filter_by(id=tx_id, user_id=current_user.id).first()
    if not tx:
        raise HTTPException(404, "Not found")
    if "category_id" in req.model_dump(exclude_none=True):
        _ensure_category_owned_by_user(db, req.category_id, current_user.id)

    root_id = tx.parent_transaction_id or tx.id
    if cascade == "all":
        siblings = db.query(Transaction).filter(
            (Transaction.id == root_id) | (Transaction.parent_transaction_id == root_id)
        ).filter_by(user_id=current_user.id).all()
    elif cascade == "future":
        siblings = db.query(Transaction).filter(
            ((Transaction.id == root_id) | (Transaction.parent_transaction_id == root_id)),
            Transaction.date >= tx.date,
        ).filter_by(user_id=current_user.id).all()
    else:
        siblings = [tx]

    # Bulk-load all payment methods used by siblings (avoids N+1 queries)
    pm_ids = {t.payment_method_id for t in siblings}
    pms_map = {
        pm.id: pm
        for pm in db.query(PaymentMethod).filter(PaymentMethod.id.in_(pm_ids)).all()
    }

    # Split fields: date must only apply to the target transaction, not siblings
    cascade_fields = {k: v for k, v in req.model_dump(exclude_none=True).items() if k != "date"}
    target_fields = req.model_dump(exclude_none=True)

    for t in siblings:
        fields = target_fields if t.id == tx_id else cascade_fields
        for field, val in fields.items():
            setattr(t, field, val)
        # Recompute billing_month — fail hard if PM was deleted
        pm = pms_map.get(t.payment_method_id)
        if not pm:
            raise HTTPException(422, f"Payment method {t.payment_method_id!r} no longer exists")
        t.billing_month = str(billing_month(pm.type, parse_date(t.date).date()))
    db.commit()
    db.refresh(tx)
    return tx

@router.delete("/{tx_id}")
def delete_transaction(
    tx_id: str,
    cascade: Literal["single", "future", "all"] = Query("single"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tx = db.query(Transaction).filter_by(id=tx_id, user_id=current_user.id).first()
    if not tx:
        raise HTTPException(404, "Not found")

    root_id = tx.parent_transaction_id or tx.id
    if cascade == "all":
        to_delete = db.query(Transaction).filter(
            (Transaction.id == root_id) | (Transaction.parent_transaction_id == root_id)
        ).filter_by(user_id=current_user.id).all()
    elif cascade == "future":
        to_delete = db.query(Transaction).filter(
            ((Transaction.id == root_id) | (Transaction.parent_transaction_id == root_id)),
            Transaction.date >= tx.date,
        ).filter_by(user_id=current_user.id).all()
    else:
        _promote_transaction_series_root_if_needed(db, current_user.id, tx)
        to_delete = [tx]

    for t in to_delete:
        db.delete(t)
    db.commit()
    return {"ok": True}
