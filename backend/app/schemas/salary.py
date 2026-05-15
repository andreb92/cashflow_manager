from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


class SalaryConfigCreate(BaseModel):
    valid_from: str
    ral: float = Field(ge=0)
    employer_contrib_rate: float = Field(0.0, ge=0, le=1)
    voluntary_contrib_rate: float = Field(0.0, ge=0, le=1)
    regional_tax_rate: float = Field(0.0, ge=0, le=1)
    municipal_tax_rate: float = Field(0.0, ge=0, le=1)
    meal_vouchers_annual: float = Field(0.0, ge=0)
    welfare_annual: float = Field(0.0, ge=0)
    salary_months: int = Field(12, ge=1, le=14)
    manual_net_override: Optional[float] = Field(default=None, ge=0)
