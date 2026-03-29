from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.deps import get_db, get_current_user
from app.models.user import User
from app.models.asset import Asset
from app.services.assets import compute_assets

router = APIRouter(prefix="/assets", tags=["assets"])

class OverrideRequest(BaseModel):
    manual_override: Optional[float] = None
    notes: Optional[str] = None

@router.get("/{year}")
def list_assets(year: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = compute_assets(current_user.id, year, db)
    return [r.__dict__ for r in rows]

@router.put("/{year}/{asset_type}/{asset_name}")
def set_override(
    year: int, asset_type: str, asset_name: str,
    req: OverrideRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.query(Asset).filter_by(
        user_id=current_user.id, year=year, asset_type=asset_type, asset_name=asset_name
    ).first()
    if row:
        row.manual_override = req.manual_override
        row.notes = req.notes
    else:
        db.add(Asset(
            user_id=current_user.id, year=year, asset_type=asset_type,
            asset_name=asset_name, manual_override=req.manual_override, notes=req.notes,
        ))
    db.commit()
    return {"ok": True}
