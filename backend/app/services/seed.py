from sqlalchemy.orm import Session
from app.models.tax import TaxConfig
from app.models.category import Category
from app.models.user import gen_uuid

DEFAULT_CATEGORIES = [
    ("Housing", "Home"),
    ("Housing", "Garage"),
    ("Housing", "Bills"),
    ("Mobility", "Car"),
    ("Mobility", "Fuel"),
    ("Bills", "Phone + Internet"),
    ("Bills", "Bills"),
    ("Personal", "Food"),
    ("Personal", "Wellness"),
    ("Leisure", "Trip"),
    ("Leisure", "Restaurants"),
    ("Leisure", "Vars"),
    ("Leisure", "Gifts"),
    ("Salary", "Income"),
    ("Saving", "Saving"),
    ("Saving", "Transfer"),
    ("Saving", "Investments"),
    ("Saving", "Inv-Transfer"),
    ("Saving", "Inv-Outcome"),
]

TAX_2026 = {
    "valid_from": "2026-01-01",
    "inps_rate": 0.0919,
    "irpef_band1_rate": 0.23,
    "irpef_band1_limit": 28000,
    "irpef_band2_rate": 0.33,
    "irpef_band2_limit": 50000,
    "irpef_band3_rate": 0.43,
    "employment_deduction_band1_limit": 15000,
    "employment_deduction_band1_amount": 1955,
    "employment_deduction_band2_limit": 28000,
    "employment_deduction_band2_base": 1910,
    "employment_deduction_band2_variable": 1190,
    "employment_deduction_band2_range": 13000,
    "employment_deduction_band3_limit": 50000,
    "employment_deduction_band3_base": 1910,
    "employment_deduction_band3_range": 22000,
    "pension_deductibility_cap": 5300.00,
    "employment_deduction_floor": 690.00,
}


def seed_tax_config(db: Session) -> None:
    existing = db.query(TaxConfig).filter_by(valid_from=TAX_2026["valid_from"]).first()
    if not existing:
        db.add(TaxConfig(id=gen_uuid(), **TAX_2026))
        db.commit()


def get_default_categories() -> list[tuple[str, str]]:
    return list(DEFAULT_CATEGORIES)


def seed_user_categories(user_id: str, db: Session) -> None:
    for cat_type, cat_sub in DEFAULT_CATEGORIES:
        db.add(Category(
            id=gen_uuid(), user_id=user_id, type=cat_type, sub_type=cat_sub,
            is_active=(cat_type != "Saving"),
        ))
    db.commit()
