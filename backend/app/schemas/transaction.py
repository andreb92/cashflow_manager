from __future__ import annotations
import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional


def _validate_iso_date(v: str) -> str:
    try:
        datetime.date.fromisoformat(v)
    except ValueError:
        raise ValueError(f"Invalid date format: {v!r} (expected YYYY-MM-DD)")
    return v


class TransactionCreate(BaseModel):
    date: str
    detail: str
    amount: Decimal = Field(gt=0)
    payment_method_id: str
    category_id: Optional[str] = None
    transaction_direction: Literal['income', 'debit', 'credit']
    recurrence_months: Optional[int] = Field(None, ge=1, le=60)
    notes: Optional[str] = None

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        return _validate_iso_date(v)

class TransactionUpdate(BaseModel):
    # NOTE: payment_method_id is intentionally omitted from this schema.
    # Changing the payment method would require recomputing billing_month (which is
    # derived from the payment method's billing cycle) and cascading updates to any
    # related installment or recurring child transactions. Allowing it here would
    # silently leave billing_month stale and break financial reporting. Users must
    # delete and recreate the transaction to change its payment method.
    date: Optional[str] = None
    detail: Optional[str] = None
    amount: Optional[float] = Field(None, gt=0)
    category_id: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        return _validate_iso_date(v)
