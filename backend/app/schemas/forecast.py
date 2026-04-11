from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal, Optional


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
    adjustment_type: Literal["fixed", "percentage"] = "fixed"
