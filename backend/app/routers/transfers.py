from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Literal
from dateutil.parser import parse as parse_date
from dateutil.relativedelta import relativedelta
from app.deps import get_db, get_current_user
from app.models.user import User
from app.models.transfer import Transfer
from app.models.payment_method import PaymentMethod
from app.schemas.transfer import TransferCreate, TransferUpdate

router = APIRouter(prefix="/transfers", tags=["transfers"])


def _resolve_pm_id(db: Session, user_id: str, account_type: str, account_name: str) -> Optional[str]:
    """Look up a PaymentMethod id by (user_id, name) when the account is a bank.
    Returns None for non-bank account types (saving/investment/pension have no PM row)
    or when no PM matches (defensive — name is user-editable).
    """
    if account_type != "bank" or not account_name:
        return None
    pm = db.query(PaymentMethod).filter_by(user_id=user_id, name=account_name).first()
    return pm.id if pm else None


def _promote_transfer_series_root_if_needed(db: Session, user_id: str, transfer: Transfer) -> None:
    """When deleting a recurring root as single, promote the next row to root.

    Without this, deleting the root can violate the self-FK because children still
    reference the deleted id.
    """
    if transfer.parent_transfer_id is not None:
        return

    children = (
        db.query(Transfer)
        .filter_by(user_id=user_id, parent_transfer_id=transfer.id)
        .order_by(Transfer.date.asc(), Transfer.created_at.asc(), Transfer.id.asc())
        .all()
    )
    if not children:
        return

    new_root = children[0]
    new_root.parent_transfer_id = None
    for child in children[1:]:
        child.parent_transfer_id = new_root.id

@router.get("")
def list_transfers(
    billing_month: Optional[str] = None,
    from_account: Optional[str] = None,
    to_account: Optional[str] = None,
    limit: Optional[int] = None, offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if billing_month is None and from_account is None and to_account is None and limit is None:
        raise HTTPException(400, "At least one of billing_month, from_account, to_account, or limit is required")
    q = db.query(Transfer).filter_by(user_id=current_user.id)
    if billing_month:
        q = q.filter(Transfer.billing_month.startswith(billing_month))
    if from_account:
        q = q.filter_by(from_account_name=from_account)
    if to_account:
        q = q.filter_by(to_account_name=to_account)
    # Keep pagination stable when many rows share the same date.
    q = q.order_by(Transfer.date.desc(), Transfer.created_at.desc(), Transfer.id.desc()).offset(offset)
    if limit is not None:
        q = q.limit(limit)
    return q.all()

@router.post("")
def create_transfer(req: TransferCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tx_date = parse_date(req.date).date()
    bm = tx_date.replace(day=1)  # transfers always bill current month

    from_pm_id = _resolve_pm_id(db, current_user.id, req.from_account_type, req.from_account_name)
    to_pm_id = _resolve_pm_id(db, current_user.id, req.to_account_type, req.to_account_name)

    if req.recurrence_months:
        first = None
        for i in range(req.recurrence_months):
            occ_date = tx_date + relativedelta(months=i)
            t = Transfer(
                user_id=current_user.id, date=str(occ_date), detail=req.detail,
                amount=req.amount, from_account_type=req.from_account_type,
                from_account_name=req.from_account_name, to_account_type=req.to_account_type,
                to_account_name=req.to_account_name,
                billing_month=str(occ_date.replace(day=1)),
                recurrence_months=req.recurrence_months, notes=req.notes,
                from_payment_method_id=from_pm_id,
                to_payment_method_id=to_pm_id,
            )
            db.add(t)
            db.flush()
            if i == 0:
                first = t
            else:
                t.parent_transfer_id = first.id
        db.commit()
        db.refresh(first)
        return first

    t = Transfer(
        user_id=current_user.id, date=req.date, detail=req.detail,
        amount=req.amount, from_account_type=req.from_account_type,
        from_account_name=req.from_account_name, to_account_type=req.to_account_type,
        to_account_name=req.to_account_name, billing_month=str(bm), notes=req.notes,
        from_payment_method_id=from_pm_id,
        to_payment_method_id=to_pm_id,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t

@router.get("/{transfer_id}")
def get_transfer(transfer_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    t = db.query(Transfer).filter_by(id=transfer_id, user_id=current_user.id).first()
    if not t:
        raise HTTPException(404, "Not found")
    return t

@router.put("/{transfer_id}")
def update_transfer(
    transfer_id: str, req: TransferUpdate,
    cascade: Literal["single", "future", "all"] = Query("single"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = db.query(Transfer).filter_by(id=transfer_id, user_id=current_user.id).first()
    if not t:
        raise HTTPException(404, "Not found")
    root_id = t.parent_transfer_id or t.id
    if cascade == "all":
        rows = db.query(Transfer).filter(
            (Transfer.id == root_id) | (Transfer.parent_transfer_id == root_id)
        ).filter_by(user_id=current_user.id).all()
    elif cascade == "future":
        rows = db.query(Transfer).filter(
            ((Transfer.id == root_id) | (Transfer.parent_transfer_id == root_id)),
            Transfer.date >= t.date,
        ).filter_by(user_id=current_user.id).all()
    else:
        rows = [t]
    # Split fields: date must only apply to the target row, not siblings
    cascade_fields = {k: v for k, v in req.model_dump(exclude_none=True).items() if k != "date"}
    target_fields = req.model_dump(exclude_none=True)

    for row in rows:
        fields = target_fields if row.id == transfer_id else cascade_fields
        for field, val in fields.items():
            setattr(row, field, val)
        # Recompute billing_month — transfers always bill the current month (no credit-card shift)
        row.billing_month = str(parse_date(row.date).date().replace(day=1))
    db.commit()
    db.refresh(t)
    return t

@router.delete("/{transfer_id}")
def delete_transfer(
    transfer_id: str,
    cascade: Literal["single", "future", "all"] = Query("single"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = db.query(Transfer).filter_by(id=transfer_id, user_id=current_user.id).first()
    if not t:
        raise HTTPException(404, "Not found")
    root_id = t.parent_transfer_id or t.id
    if cascade == "all":
        to_del = db.query(Transfer).filter(
            (Transfer.id == root_id) | (Transfer.parent_transfer_id == root_id)
        ).filter_by(user_id=current_user.id).all()
    elif cascade == "future":
        to_del = db.query(Transfer).filter(
            ((Transfer.id == root_id) | (Transfer.parent_transfer_id == root_id)),
            Transfer.date >= t.date,
        ).filter_by(user_id=current_user.id).all()
    else:
        _promote_transfer_series_root_if_needed(db, current_user.id, t)
        to_del = [t]
    for row in to_del:
        db.delete(row)
    db.commit()
    return {"ok": True}
