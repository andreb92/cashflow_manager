from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, Field
from app.deps import get_db, get_current_user
from app.models.user import User
from app.models.salary import SalaryConfig
from app.services.salary import calculate_salary
from app.services.tax import resolve_tax_config

router = APIRouter(prefix="/salary", tags=["salary"])


class SalaryConfigCreate(BaseModel):
    valid_from: str
    ral: float
    employer_contrib_rate: float = 0.0
    voluntary_contrib_rate: float = 0.0
    regional_tax_rate: float = 0.0
    municipal_tax_rate: float = 0.0
    meal_vouchers_annual: float = 0.0
    welfare_annual: float = 0.0
    salary_months: int = Field(12, ge=1)
    manual_net_override: Optional[float] = None


# /calculate MUST be registered before /{salary_id} to avoid route shadowing
@router.get("/calculate")
def preview_salary(
    as_of: str = Query(...),
    ral: float = Query(...),
    employer_contrib_rate: float = Query(0.0),
    voluntary_contrib_rate: float = Query(0.0),
    regional_tax_rate: float = Query(0.0),
    municipal_tax_rate: float = Query(0.0),
    meal_vouchers_annual: float = Query(0.0),
    welfare_annual: float = Query(0.0),
    salary_months: int = Query(12, ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tax_cfg = resolve_tax_config(db, as_of, current_user.id)
    if not tax_cfg:
        raise HTTPException(422, "No tax config found for the given period")

    class _Cfg:
        pass
    cfg = _Cfg()
    for k, v in dict(
        ral=ral,
        employer_contrib_rate=employer_contrib_rate,
        voluntary_contrib_rate=voluntary_contrib_rate,
        regional_tax_rate=regional_tax_rate,
        municipal_tax_rate=municipal_tax_rate,
        meal_vouchers_annual=meal_vouchers_annual,
        welfare_annual=welfare_annual,
        salary_months=salary_months,
    ).items():
        setattr(cfg, k, v)
    return calculate_salary(cfg, tax_cfg).__dict__


@router.get("")
def list_salary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(SalaryConfig).filter_by(user_id=current_user.id).order_by(SalaryConfig.valid_from).all()


@router.post("")
def create_salary(req: SalaryConfigCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tax_cfg = resolve_tax_config(db, req.valid_from[:7], current_user.id)
    breakdown = calculate_salary(req, tax_cfg) if tax_cfg else None
    sc = SalaryConfig(user_id=current_user.id, **req.model_dump(),
                      computed_net_monthly=breakdown.net_monthly if breakdown else 0)
    db.add(sc)
    db.commit()
    db.refresh(sc)
    return sc


@router.put("/{salary_id}")
def update_salary(salary_id: str, req: SalaryConfigCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sc = db.query(SalaryConfig).filter_by(id=salary_id, user_id=current_user.id).first()
    if not sc:
        raise HTTPException(404, "Not found")
    for field, val in req.model_dump(exclude_none=True).items():
        setattr(sc, field, val)
    tax_cfg = resolve_tax_config(db, sc.valid_from[:7], current_user.id)
    if tax_cfg:
        sc.computed_net_monthly = calculate_salary(sc, tax_cfg).net_monthly
    db.commit()
    db.refresh(sc)
    return sc


@router.delete("/{salary_id}")
def delete_salary(salary_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sc = db.query(SalaryConfig).filter_by(id=salary_id, user_id=current_user.id).first()
    if not sc:
        raise HTTPException(404, "Not found")
    earliest = db.query(SalaryConfig).filter_by(user_id=current_user.id).order_by(SalaryConfig.valid_from).first()
    if earliest and earliest.id == salary_id:
        raise HTTPException(400, "Cannot delete the earliest salary config row")
    db.delete(sc)
    db.commit()
    return {"ok": True}
