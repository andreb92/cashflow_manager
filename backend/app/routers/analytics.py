from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.deps import get_db, get_current_user
from app.models.user import User
from app.services.analytics import category_spending, transfer_spending

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/categories")
def analytics_categories(
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    category_ids: Optional[str] = Query(None),
    payment_method_ids: Optional[str] = Query(None),
    direction: str = Query("all"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cat_ids = category_ids.split(",") if category_ids else None
    pm_ids = payment_method_ids.split(",") if payment_method_ids else None
    return category_spending(current_user.id, from_, to, db, cat_ids, pm_ids, direction)


@router.get("/transfers")
def analytics_transfers(
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return transfer_spending(current_user.id, from_, to, db)
