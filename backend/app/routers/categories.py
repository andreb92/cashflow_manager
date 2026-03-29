from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.deps import get_db, get_current_user
from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction

router = APIRouter(prefix="/categories", tags=["categories"])

class CategoryCreate(BaseModel):
    type: str
    sub_type: str

class CategoryUpdate(BaseModel):
    type: Optional[str] = None
    sub_type: Optional[str] = None
    is_active: Optional[bool] = None

@router.get("")
def list_categories(active_only: bool = False, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(Category).filter_by(user_id=current_user.id)
    if active_only:
        q = q.filter_by(is_active=True)
    return q.all()

@router.post("")
def create_category(req: CategoryCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cat = Category(user_id=current_user.id, type=req.type, sub_type=req.sub_type)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat

@router.put("/{cat_id}")
def update_category(cat_id: str, req: CategoryUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cat = db.query(Category).filter_by(id=cat_id, user_id=current_user.id).first()
    if not cat:
        raise HTTPException(404, "Not found")
    for field, val in req.model_dump(exclude_none=True).items():
        setattr(cat, field, val)
    db.commit()
    db.refresh(cat)
    return cat

@router.delete("/{cat_id}")
def delete_category(cat_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cat = db.query(Category).filter_by(id=cat_id, user_id=current_user.id).first()
    if not cat:
        raise HTTPException(404, "Not found")
    if db.query(Transaction).filter_by(category_id=cat_id, user_id=current_user.id).first():
        raise HTTPException(409, "Category referenced by transactions; deactivate instead")
    db.delete(cat)
    db.commit()
    return {"ok": True}
