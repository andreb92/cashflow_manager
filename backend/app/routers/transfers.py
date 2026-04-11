from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Literal
from dateutil.parser import parse as parse_date
from dateutil.relativedelta import relativedelta
from app.deps import get_db, get_current_user
from app.models.user import User
from app.models.transfer import Transfer
from app.schemas.transfer import TransferCreate, TransferUpdate

router = APIRouter(prefix="/transfers", tags=["transfers"])

@router.get("")
def list_transfers(
    billing_month: Optional[str] = None,
    from_account: Optional[str] = None,
    to_account: Optional[str] = None,
    limit: Optional[int] = None, offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Transfer).filter_by(user_id=current_user.id)
    if billing_month:
        q = q.filter(Transfer.billing_month.startswith(billing_month))
    if from_account:
        q = q.filter_by(from_account_name=from_account)
    if to_account:
        q = q.filter_by(to_account_name=to_account)
    q = q.order_by(Transfer.date.desc()).offset(offset)
    if limit is not None:
        q = q.limit(limit)
    return q.all()

@router.post("")
def create_transfer(req: TransferCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tx_date = parse_date(req.date).date()
    bm = tx_date.replace(day=1)  # transfers always bill current month

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
        to_del = [t]
    for row in to_del:
        db.delete(row)
    db.commit()
    return {"ok": True}
