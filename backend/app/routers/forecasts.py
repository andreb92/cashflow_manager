from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, Field
from app.deps import get_db, get_current_user
from app.models.user import User
from app.models.forecast import Forecast, ForecastLine, ForecastAdjustment
from app.services.forecasting import auto_generate_lines, project_forecast

router = APIRouter(prefix="/forecasts", tags=["forecasts"])


class ForecastCreate(BaseModel):
    name: str
    base_year: int
    projection_years: int


class ForecastUpdate(BaseModel):
    name: Optional[str] = None
    projection_years: Optional[int] = Field(default=None, ge=1)


class ForecastLineCreate(BaseModel):
    detail: str
    base_amount: float
    category_id: Optional[str] = None
    payment_method_id: Optional[str] = None
    billing_day: int = 1
    notes: Optional[str] = None


class AdjustmentCreate(BaseModel):
    valid_from: str    # YYYY-MM-DD
    new_amount: float


def _forecast_detail(forecast: Forecast, db: Session) -> dict:
    lines = db.query(ForecastLine).filter_by(forecast_id=forecast.id).all()
    # Bulk-load all adjustments in one query
    line_ids = [line.id for line in lines]
    all_adjs = (
        db.query(ForecastAdjustment)
        .filter(ForecastAdjustment.forecast_line_id.in_(line_ids))
        .all()
        if line_ids else []
    )
    adjs_by_line: dict[str, list] = {lid: [] for lid in line_ids}
    for a in all_adjs:
        adjs_by_line[a.forecast_line_id].append(a)

    lines_out = []
    for line in lines:
        adjs = adjs_by_line.get(line.id, [])
        lines_out.append({
            "id": line.id, "detail": line.detail, "category_id": line.category_id,
            "base_amount": float(line.base_amount), "billing_day": line.billing_day,
            "payment_method_id": line.payment_method_id, "notes": line.notes,
            "adjustments": [
                {"id": a.id, "valid_from": a.valid_from, "new_amount": float(a.new_amount)}
                for a in adjs
            ],
        })
    return {
        "id": forecast.id, "name": forecast.name,
        "base_year": forecast.base_year, "projection_years": forecast.projection_years,
        "created_at": str(forecast.created_at), "updated_at": str(forecast.updated_at),
        "lines": lines_out,
    }


@router.get("")
def list_forecasts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Forecast).filter_by(user_id=current_user.id).all()


@router.post("")
def create_forecast(req: ForecastCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    fc = Forecast(
        user_id=current_user.id, name=req.name, base_year=req.base_year,
        projection_years=req.projection_years,
    )
    db.add(fc)
    db.flush()
    auto_generate_lines(fc, db)
    db.commit()
    db.refresh(fc)
    return _forecast_detail(fc, db)


@router.get("/{fc_id}")
def get_forecast(fc_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    fc = db.query(Forecast).filter_by(id=fc_id, user_id=current_user.id).first()
    if not fc:
        raise HTTPException(404, "Not found")
    return _forecast_detail(fc, db)


@router.put("/{fc_id}")
def update_forecast(fc_id: str, req: ForecastUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    fc = db.query(Forecast).filter_by(id=fc_id, user_id=current_user.id).first()
    if not fc:
        raise HTTPException(404, "Not found")
    if req.name is not None:
        fc.name = req.name
    if req.projection_years is not None:
        new_end = f"{fc.base_year + req.projection_years:04d}-12-01"
        # Delete adjustments beyond new end
        for line in db.query(ForecastLine).filter_by(forecast_id=fc_id).all():
            for adj in db.query(ForecastAdjustment).filter_by(forecast_line_id=line.id).all():
                if adj.valid_from > new_end:
                    db.delete(adj)
        fc.projection_years = req.projection_years
    db.commit()
    db.refresh(fc)
    return _forecast_detail(fc, db)


@router.delete("/{fc_id}")
def delete_forecast(fc_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    fc = db.query(Forecast).filter_by(id=fc_id, user_id=current_user.id).first()
    if not fc:
        raise HTTPException(404, "Not found")
    db.delete(fc)
    db.commit()
    return {"ok": True}


@router.get("/{fc_id}/projection")
def get_projection(fc_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    fc = db.query(Forecast).filter_by(id=fc_id, user_id=current_user.id).first()
    if not fc:
        raise HTTPException(404, "Not found")
    return project_forecast(fc_id, current_user.id, db)


@router.post("/{fc_id}/lines")
def add_line(fc_id: str, req: ForecastLineCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    fc = db.query(Forecast).filter_by(id=fc_id, user_id=current_user.id).first()
    if not fc:
        raise HTTPException(404, "Not found")
    line = ForecastLine(forecast_id=fc_id, user_id=current_user.id, **req.model_dump())
    db.add(line)
    db.commit()
    db.refresh(line)
    return {
        "id": line.id, "detail": line.detail, "category_id": line.category_id,
        "base_amount": float(line.base_amount), "billing_day": line.billing_day,
        "payment_method_id": line.payment_method_id, "notes": line.notes,
        "adjustments": [],
    }


@router.put("/{fc_id}/lines/{line_id}")
def update_line(fc_id: str, line_id: str, req: ForecastLineCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    line = db.query(ForecastLine).filter_by(id=line_id, forecast_id=fc_id, user_id=current_user.id).first()
    if not line:
        raise HTTPException(404, "Not found")
    for field, val in req.model_dump(exclude_none=True).items():
        setattr(line, field, val)
    db.commit()
    db.refresh(line)
    return line


@router.delete("/{fc_id}/lines/{line_id}")
def delete_line(fc_id: str, line_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    line = db.query(ForecastLine).filter_by(id=line_id, forecast_id=fc_id, user_id=current_user.id).first()
    if not line:
        raise HTTPException(404, "Not found")
    db.delete(line)
    db.commit()
    return {"ok": True}


@router.post("/{fc_id}/lines/{line_id}/adjustments")
def add_adjustment(
    fc_id: str, line_id: str, req: AdjustmentCreate,
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    fc = db.query(Forecast).filter_by(id=fc_id, user_id=current_user.id).first()
    if not fc:
        raise HTTPException(404, "Not found")
    line = db.query(ForecastLine).filter_by(id=line_id, forecast_id=fc_id, user_id=current_user.id).first()
    if not line:
        raise HTTPException(404, "Not found")
    # Validate valid_from is within projection period
    end_date = f"{fc.base_year + fc.projection_years:04d}-12-01"
    start_date = f"{fc.base_year + 1:04d}-01-01"
    if not (start_date <= req.valid_from <= end_date):
        raise HTTPException(422, f"valid_from must be between {start_date} and {end_date}")
    adj = ForecastAdjustment(
        forecast_line_id=line_id, user_id=current_user.id,
        valid_from=req.valid_from, new_amount=req.new_amount,
    )
    db.add(adj)
    db.commit()
    db.refresh(adj)
    return adj


@router.put("/{fc_id}/lines/{line_id}/adjustments/{adj_id}")
def update_adjustment(
    fc_id: str, line_id: str, adj_id: str, req: AdjustmentCreate,
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    adj = db.query(ForecastAdjustment).filter_by(id=adj_id, forecast_line_id=line_id, user_id=current_user.id).first()
    if not adj:
        raise HTTPException(404, "Not found")
    adj.valid_from = req.valid_from
    adj.new_amount = req.new_amount
    db.commit()
    db.refresh(adj)
    return adj


@router.delete("/{fc_id}/lines/{line_id}/adjustments/{adj_id}")
def delete_adjustment(
    fc_id: str, line_id: str, adj_id: str,
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    adj = db.query(ForecastAdjustment).filter_by(id=adj_id, forecast_line_id=line_id, user_id=current_user.id).first()
    if not adj:
        raise HTTPException(404, "Not found")
    db.delete(adj)
    db.commit()
    return {"ok": True}
