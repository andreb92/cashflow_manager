from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal, Optional


class ForecastCreate(BaseModel):
    name: str
    base_year: int = Field(ge=2000, le=2100)
    projection_years: int = Field(ge=1, le=10)


class ForecastUpdate(BaseModel):
    name: Optional[str] = None
    projection_years: Optional[int] = Field(default=None, ge=1, le=10)


class ForecastLineCreate(BaseModel):
    detail: str
    base_amount: float
    category_id: Optional[str] = None
    payment_method_id: Optional[str] = None
    billing_day: int = Field(default=1, ge=1, le=31)
    notes: Optional[str] = None


class AdjustmentCreate(BaseModel):
    valid_from: str    # YYYY-MM-DD
    new_amount: float
    adjustment_type: Literal["fixed", "percentage"] = "fixed"


class AdjustmentUpdate(BaseModel):
    valid_from: Optional[str] = None
    new_amount: Optional[float] = None
    adjustment_type: Optional[Literal["fixed", "percentage"]] = None
