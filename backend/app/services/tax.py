from sqlalchemy.orm import Session
from typing import Optional
from app.models.tax import TaxConfig

def resolve_tax_config(db: Session, as_of_ym: str, user_id: str) -> Optional[TaxConfig]:
    """Return the most-recent TaxConfig valid for as_of_ym scoped to user_id.
    Falls back to system rows (user_id IS NULL) if the user has no custom config."""
    as_of_date = as_of_ym[:7] + "-01"
    row = (
        db.query(TaxConfig)
        .filter(TaxConfig.valid_from <= as_of_date, TaxConfig.user_id == user_id)
        .order_by(TaxConfig.valid_from.desc())
        .first()
    )
    if row:
        return row
    return (
        db.query(TaxConfig)
        .filter(TaxConfig.valid_from <= as_of_date, TaxConfig.user_id.is_(None))
        .order_by(TaxConfig.valid_from.desc())
        .first()
    )
