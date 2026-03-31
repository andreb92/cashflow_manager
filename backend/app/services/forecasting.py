from collections import defaultdict

from sqlalchemy.orm import Session
from app.models.forecast import Forecast, ForecastLine, ForecastAdjustment
from app.models.transaction import Transaction


def auto_generate_lines(forecast: Forecast, db: Session) -> None:
    """
    Create ForecastLines from recurring transactions in base_year.
    Groups by root recurring transaction; uses average monthly amount.
    Bulk-loads all siblings in one query to avoid N+1 per root.
    """
    year = forecast.base_year
    # Look back 2 years so recurring transactions that started before base_year
    # are still captured; children are not restricted to this window.
    history_start = f"{year - 2:04d}-01-01"
    year_end = f"{year:04d}-12-31"

    recurring_roots = (
        db.query(Transaction)
        .filter_by(user_id=forecast.user_id)
        .filter(
            Transaction.recurrence_months.isnot(None),
            Transaction.date >= history_start,
            Transaction.date <= year_end,
            Transaction.parent_transaction_id.is_(None),  # roots only
        )
        .all()
    )
    if not recurring_roots:
        return

    root_ids = [tx.id for tx in recurring_roots]

    # Bulk-load all siblings (roots + children) in one query.
    # No date restriction on siblings so we capture all occurrences regardless
    # of when the root was created.
    all_siblings = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == forecast.user_id,
            (Transaction.id.in_(root_ids)) | (Transaction.parent_transaction_id.in_(root_ids)),
        )
        .all()
    )

    # Group siblings by root_id
    siblings_by_root: dict[str, list] = defaultdict(list)
    for s in all_siblings:
        root = s.parent_transaction_id or s.id
        siblings_by_root[root].append(s)

    for tx in recurring_roots:
        siblings = siblings_by_root[tx.id]
        avg_amount = sum(float(s.amount) for s in siblings) / max(len(siblings), 1)
        db.add(ForecastLine(
            forecast_id=forecast.id,
            user_id=forecast.user_id,
            source_transaction_id=tx.id,
            category_id=tx.category_id,
            detail=tx.detail,
            base_amount=avg_amount,
            payment_method_id=tx.payment_method_id,
            billing_day=1,
        ))


def project_forecast(forecast_id: str, user_id: str, db: Session) -> dict:
    """
    Compute month-by-month projection for all lines.
    Projection period: base_year+1 through base_year+projection_years.
    effective_amount(line, month) = highest valid_from adjustment <= month, else base_amount.
    """
    forecast = db.query(Forecast).filter(
        Forecast.id == forecast_id, Forecast.user_id == user_id
    ).first()
    if not forecast:
        return {}

    start_year = forecast.base_year + 1
    end_year = forecast.base_year + forecast.projection_years
    period_from = f"{start_year:04d}-01"
    period_to = f"{end_year:04d}-12"

    lines = db.query(ForecastLine).filter_by(forecast_id=forecast_id).all()
    # Bulk-load all adjustments in one query
    line_ids = [line.id for line in lines]
    all_adjs = (
        db.query(ForecastAdjustment)
        .filter(ForecastAdjustment.forecast_line_id.in_(line_ids))
        .order_by(ForecastAdjustment.valid_from)
        .all()
        if line_ids else []
    )
    adj_by_line: dict[str, list] = {lid: [] for lid in line_ids}
    for a in all_adjs:
        adj_by_line[a.forecast_line_id].append(a)

    result_lines = []
    monthly_totals = {}

    for line in lines:
        adjs = adj_by_line[line.id]
        months_data = []
        for year in range(start_year, end_year + 1):
            for month in range(1, 13):
                month_str = f"{year:04d}-{month:02d}"
                month_first = f"{year:04d}-{month:02d}-01"
                # Find applicable adjustment
                applicable = [a for a in adjs if a.valid_from <= month_first]
                if applicable:
                    effective = float(max(applicable, key=lambda a: a.valid_from).new_amount)
                else:
                    effective = float(line.base_amount)
                months_data.append({"month": month_str, "effective_amount": effective})
                monthly_totals[month_str] = monthly_totals.get(month_str, 0) + effective

        result_lines.append({
            "line_id": line.id,
            "detail": line.detail,
            "category_id": line.category_id,
            "base_amount": float(line.base_amount),
            "billing_day": line.billing_day,
            "adjustments": [
                {"id": a.id, "valid_from": a.valid_from[:7], "new_amount": float(a.new_amount)}
                for a in adjs
            ],
            "months": months_data,
        })

    # Yearly totals
    yearly_totals = {}
    for month_str, total in monthly_totals.items():
        year_str = month_str[:4]
        yearly_totals[year_str] = yearly_totals.get(year_str, 0) + total

    return {
        "forecast_id": forecast_id,
        "base_year": forecast.base_year,
        "projection_years": forecast.projection_years,
        "period": {"from": period_from, "to": period_to},
        "lines": result_lines,
        "monthly_totals": [{"month": k, "total": round(v, 2)} for k, v in sorted(monthly_totals.items())],
        "yearly_totals": [{"year": int(k), "total": round(v, 2)} for k, v in sorted(yearly_totals.items())],
    }
