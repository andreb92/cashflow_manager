from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.deps import get_db, get_current_user
from app.models.user import User
from app.models.payment_method import PaymentMethod, MainBankHistory
from app.schemas.payment_method import PaymentMethodCreate, PaymentMethodUpdate, SetMainBankRequest
from app.models.transfer import Transfer

router = APIRouter(prefix="/payment-methods", tags=["payment-methods"])


def _validate_linked_bank_id(db: Session, linked_bank_id: str | None, user_id: str) -> None:
    if linked_bank_id and not db.query(PaymentMethod).filter_by(id=linked_bank_id, user_id=user_id).first():
        raise HTTPException(422, "linked_bank_id not found or belongs to another user")

@router.get("")
def list_methods(
    active_only: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(PaymentMethod).filter_by(user_id=current_user.id)
    if active_only:
        q = q.filter_by(is_active=True)
    return q.all()

@router.post("")
def create_method(req: PaymentMethodCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _validate_linked_bank_id(db, req.linked_bank_id, current_user.id)
    pm = PaymentMethod(user_id=current_user.id, **req.model_dump())
    db.add(pm)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(422, "A payment method with this name already exists")
    db.refresh(pm)
    return pm

# NOTE: /main-bank-history must be registered BEFORE /{pm_id} to avoid route shadowing
@router.get("/main-bank-history")
def main_bank_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(MainBankHistory)
        .filter_by(user_id=current_user.id)
        .order_by(MainBankHistory.valid_from)
        .all()
    )

@router.put("/{pm_id}")
def update_method(pm_id: str, req: PaymentMethodUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pm = db.query(PaymentMethod).filter_by(id=pm_id, user_id=current_user.id).first()
    if not pm:
        raise HTTPException(404, "Not found")
    old_name = pm.name
    if "linked_bank_id" in req.model_dump(exclude_none=True):
        _validate_linked_bank_id(db, req.linked_bank_id, current_user.id)
    for field, val in req.model_dump(exclude_none=True).items():
        setattr(pm, field, val)
    # Cascade name change to all transfers referencing this account name
    if req.name and req.name != old_name:
        (
            db.query(Transfer)
            .filter_by(user_id=current_user.id, from_account_name=old_name)
            .update({"from_account_name": req.name})
        )
        (
            db.query(Transfer)
            .filter_by(user_id=current_user.id, to_account_name=old_name)
            .update({"to_account_name": req.name})
        )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(422, "A payment method with this name already exists")
    db.refresh(pm)
    return pm

@router.post("/{pm_id}/set-main-bank")
def set_main_bank(pm_id: str, req: SetMainBankRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_main = db.query(PaymentMethod).filter_by(id=pm_id, user_id=current_user.id).first()
    if not new_main:
        raise HTTPException(404, "Not found")
    if new_main.type != "bank":
        raise HTTPException(422, "Only bank-type accounts can be set as main bank")
    if not new_main.is_active:
        raise HTTPException(422, "Cannot set an inactive account as main bank")
    if req.opening_balance < 0:
        raise HTTPException(422, "Opening balance must be >= 0")
    old_main = db.query(PaymentMethod).filter_by(user_id=current_user.id, is_main_bank=True).first()
    if old_main:
        old_main.is_main_bank = False
    new_main.is_main_bank = True
    today_first = datetime.now(timezone.utc).date().replace(day=1)
    db.add(MainBankHistory(
        user_id=current_user.id, payment_method_id=pm_id,
        valid_from=today_first.isoformat(), opening_balance=req.opening_balance,
    ))
    db.commit()
    return {"ok": True}
