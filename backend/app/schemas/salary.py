from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


class SalaryConfigCreate(BaseModel):
    valid_from: str
    ral: float
    employer_contrib_rate: float = 0.0
    voluntary_contrib_rate: float = 0.0
    regional_tax_rate: float = 0.0
    municipal_tax_rate: float = 0.0
    meal_vouchers_annual: float = 0.0
    welfare_annual: float = 0.0
    salary_months: int = Field(12, ge=1)
    manual_net_override: Optional[float] = None
