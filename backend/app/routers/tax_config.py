from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.deps import get_db, get_current_user
from app.models.user import User
from app.models.tax import TaxConfig
from pydantic import BaseModel

router = APIRouter(prefix="/tax-config", tags=["tax-config"])

class TaxConfigCreate(BaseModel):
    valid_from: str
    inps_rate: float = 0.0919
    irpef_band1_rate: float = 0.23
    irpef_band1_limit: float = 28000
    irpef_band2_rate: float = 0.33
    irpef_band2_limit: float = 50000
    irpef_band3_rate: float = 0.43
    employment_deduction_band1_limit: float = 15000
    employment_deduction_band1_amount: float = 1955
    employment_deduction_band2_limit: float = 28000
    employment_deduction_band2_base: float = 1910
    employment_deduction_band2_variable: float = 1190
    employment_deduction_band2_range: float = 13000
    employment_deduction_band3_limit: float = 50000
    employment_deduction_band3_base: float = 1910
    employment_deduction_band3_range: float = 22000
    pension_deductibility_cap: float = 5300.00
    employment_deduction_floor: float = 690.00

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
    row = db.query(TaxConfig).filter_by(id=config_id).first()
    if not row:
        raise HTTPException(404, "Not found")
    if row.user_id != current_user.id:
        raise HTTPException(403, "Cannot modify a system-seeded or another user's tax config")
    for field, val in req.model_dump(exclude_none=True).items():
        setattr(row, field, val)
    db.commit()
    db.refresh(row)
    return row

@router.delete("/{config_id}")
def delete_tax_config(config_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(TaxConfig).filter_by(id=config_id).first()
    if not row:
        raise HTTPException(404, "Not found")
    if row.user_id != current_user.id:
        raise HTTPException(403, "Cannot delete a system-seeded or another user's tax config")
    earliest = db.query(TaxConfig).order_by(TaxConfig.valid_from).first()
    if earliest and earliest.id == config_id:
        raise HTTPException(400, "Cannot delete the earliest tax config row")
    db.delete(row)
    db.commit()
    return {"ok": True}
