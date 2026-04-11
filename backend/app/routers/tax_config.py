from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.deps import get_db, get_current_user
from app.models.user import User
from app.models.tax import TaxConfig
from app.schemas.tax_config import TaxConfigCreate

router = APIRouter(prefix="/tax-config", tags=["tax-config"])


@router.get("")
def list_tax_config(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(TaxConfig)
        .filter(
            (TaxConfig.user_id == None) | (TaxConfig.user_id == current_user.id)  # noqa: E711
        )
        .order_by(TaxConfig.valid_from)
        .all()
    )

@router.post("")
def create_tax_config(req: TaxConfigCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = TaxConfig(**req.model_dump(), user_id=current_user.id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row

@router.put("/{config_id}")
def update_tax_config(config_id: str, req: TaxConfigCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Atomically verify the row belongs to this user to avoid TOCTOU: check ownership
    # in a single query. Distinguish 404 (row missing entirely) from 403 (row exists
    # but is system-seeded or owned by another user) for accurate error reporting.
    row = db.query(TaxConfig).filter(TaxConfig.id == config_id, TaxConfig.user_id == current_user.id).first()
    if not row:
        exists = db.query(TaxConfig.id).filter(TaxConfig.id == config_id).first()
        if exists:
            raise HTTPException(403, "Cannot modify a system-seeded or another user's tax config")
        raise HTTPException(404, "Not found")
    for field, val in req.model_dump(exclude_none=True).items():
        setattr(row, field, val)
    db.commit()
    db.refresh(row)
    return row

@router.delete("/{config_id}")
def delete_tax_config(config_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Atomically verify the row belongs to this user to avoid TOCTOU: check ownership
    # in a single query. Distinguish 404 (row missing entirely) from 403 (row exists
    # but is system-seeded or owned by another user) for accurate error reporting.
    row = db.query(TaxConfig).filter(TaxConfig.id == config_id, TaxConfig.user_id == current_user.id).first()
    if not row:
        exists = db.query(TaxConfig.id).filter(TaxConfig.id == config_id).first()
        if exists:
            raise HTTPException(403, "Cannot delete a system-seeded or another user's tax config")
        raise HTTPException(404, "Not found")
    earliest = db.query(TaxConfig).filter(TaxConfig.user_id == current_user.id).order_by(TaxConfig.valid_from).first()
    if earliest and earliest.id == config_id:
        raise HTTPException(400, "Cannot delete the earliest tax config row")
    db.delete(row)
    db.commit()
    return {"ok": True}
