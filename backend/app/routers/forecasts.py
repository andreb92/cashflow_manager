from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.deps import get_db, get_current_user
from app.models.user import User
from app.models.category import Category
from app.models.payment_method import PaymentMethod
from app.models.forecast import Forecast, ForecastLine, ForecastAdjustment
from app.services.forecasting import auto_generate_lines, project_forecast
from app.schemas.forecast import ForecastCreate, ForecastUpdate, ForecastLineCreate, AdjustmentCreate

router = APIRouter(prefix="/forecasts", tags=["forecasts"])


def _ensure_category_owned_by_user(db: Session, category_id: str | None, user_id: str) -> None:
    if category_id is None:
        return
    category = db.query(Category).filter_by(id=category_id, user_id=user_id).first()
    if not category:
        raise HTTPException(422, "category_id not found")


def _ensure_payment_method_owned_by_user(db: Session, payment_method_id: str | None, user_id: str) -> None:
    if payment_method_id is None:
        return
    payment_method = db.query(PaymentMethod).filter_by(id=payment_method_id, user_id=user_id).first()
    if not payment_method:
        raise HTTPException(422, "payment_method_id not found")


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
                {
                    "id": a.id, "valid_from": a.valid_from, "new_amount": float(a.new_amount),
                    "adjustment_type": getattr(a, "adjustment_type", "fixed") or "fixed",
                }
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
        line_ids = [
            line.id for line in
            db.query(ForecastLine).filter_by(forecast_id=fc_id).all()
        ]
        if line_ids:
            db.query(ForecastAdjustment).filter(
                ForecastAdjustment.forecast_line_id.in_(line_ids),
                ForecastAdjustment.valid_from > new_end,
            ).delete(synchronize_session=False)
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
    _ensure_category_owned_by_user(db, req.category_id, current_user.id)
    _ensure_payment_method_owned_by_user(db, req.payment_method_id, current_user.id)
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
    payload = req.model_dump(exclude_none=True)
    if "category_id" in payload:
        _ensure_category_owned_by_user(db, req.category_id, current_user.id)
    if "payment_method_id" in payload:
        _ensure_payment_method_owned_by_user(db, req.payment_method_id, current_user.id)
    for field, val in payload.items():
        setattr(line, field, val)
    db.commit()
    db.refresh(line)
    adjustments = db.query(ForecastAdjustment).filter_by(forecast_line_id=line.id).all()
    return {
        "id": line.id, "detail": line.detail, "category_id": line.category_id,
        "base_amount": float(line.base_amount), "billing_day": line.billing_day,
        "payment_method_id": line.payment_method_id, "notes": line.notes,
        "adjustments": [
            {"id": a.id, "valid_from": a.valid_from, "new_amount": float(a.new_amount),
             "adjustment_type": a.adjustment_type}
            for a in adjustments
        ],
    }


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
        adjustment_type=req.adjustment_type,
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
    # Verify ownership chain: adj → line → forecast (prevents IDOR across user's own forecasts)
    fc = db.query(Forecast).filter_by(id=fc_id, user_id=current_user.id).first()
    if not fc:
        raise HTTPException(404, "Not found")
    adj = (
        db.query(ForecastAdjustment)
        .join(ForecastLine, ForecastAdjustment.forecast_line_id == ForecastLine.id)
        .filter(
            ForecastAdjustment.id == adj_id,
            ForecastAdjustment.forecast_line_id == line_id,
            ForecastLine.forecast_id == fc_id,
            ForecastAdjustment.user_id == current_user.id,
        )
        .first()
    )
    if not adj:
        raise HTTPException(404, "Not found")
    # Validate valid_from is within projection period (same check as add_adjustment)
    end_date = f"{fc.base_year + fc.projection_years:04d}-12-01"
    start_date = f"{fc.base_year + 1:04d}-01-01"
    if not (start_date <= req.valid_from <= end_date):
        raise HTTPException(422, f"valid_from must be between {start_date} and {end_date}")
    adj.valid_from = req.valid_from
    adj.new_amount = req.new_amount
    adj.adjustment_type = req.adjustment_type
    db.commit()
    db.refresh(adj)
    return adj


@router.delete("/{fc_id}/lines/{line_id}/adjustments/{adj_id}")
def delete_adjustment(
    fc_id: str, line_id: str, adj_id: str,
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    fc = db.query(Forecast).filter_by(id=fc_id, user_id=current_user.id).first()
    if not fc:
        raise HTTPException(404, "Not found")
    adj = (
        db.query(ForecastAdjustment)
        .join(ForecastLine, ForecastAdjustment.forecast_line_id == ForecastLine.id)
        .filter(
            ForecastAdjustment.id == adj_id,
            ForecastAdjustment.forecast_line_id == line_id,
            ForecastLine.forecast_id == fc_id,
            ForecastAdjustment.user_id == current_user.id,
        )
        .first()
    )
    if not adj:
        raise HTTPException(404, "Not found")
    db.delete(adj)
    db.commit()
    return {"ok": True}
