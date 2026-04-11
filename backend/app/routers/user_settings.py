from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.deps import get_db, get_current_user
from app.models.user import User, UserSetting

router = APIRouter(prefix="/user-settings", tags=["user-settings"])

ALLOWED_SETTING_KEYS = frozenset({
    "tracking_start_date",
    "onboarding_complete",
    "theme",
})


class SettingItem(BaseModel):
    key: str
    value: str


@router.get("")
def get_settings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(UserSetting).filter_by(user_id=current_user.id).all()


@router.put("")
def update_settings(items: List[SettingItem], current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for item in items:
        if item.key not in ALLOWED_SETTING_KEYS:
            raise HTTPException(status_code=422, detail=f"Unknown setting key: {item.key!r}")
        row = db.query(UserSetting).filter_by(user_id=current_user.id, key=item.key).first()
        if row:
            row.value = item.value
        else:
            db.add(UserSetting(user_id=current_user.id, key=item.key, value=item.value))
    db.commit()
    return {"ok": True}
