from sqlalchemy.orm import Session
from typing import Optional
from app.models.tax import TaxConfig

def resolve_tax_config(db: Session, as_of_ym: str) -> Optional[TaxConfig]:
    """Return TaxConfig row with highest valid_from <= first day of as_of_ym (YYYY-MM)."""
    as_of_date = as_of_ym[:7] + "-01"
    return (
        db.query(TaxConfig)
        .filter(TaxConfig.valid_from <= as_of_date)
        .order_by(TaxConfig.valid_from.desc())
        .first()
    )
