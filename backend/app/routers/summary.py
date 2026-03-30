from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.deps import get_db, get_current_user
from app.models.user import User
from app.services.summary import monthly_summary, year_monthly_summaries

router = APIRouter(prefix="/summary", tags=["summary"])

@router.get("/{year}")
def year_summary(year: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return year_monthly_summaries(current_user.id, year, db)

@router.get("/{year}/{month}")
def month_summary(year: int, month: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return monthly_summary(current_user.id, year, month, db)
