from __future__ import annotations
import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional

AccountType = Literal["bank", "saving", "investment", "pension"]


def _validate_iso_date(v: str) -> str:
    try:
        datetime.date.fromisoformat(v)
    except ValueError:
        raise ValueError(f"Invalid date format: {v!r} (expected YYYY-MM-DD)")
    return v


class TransferCreate(BaseModel):
    date: str
    detail: str = ""
    amount: float = Field(gt=0)
    from_account_type: AccountType
    from_account_name: str
    to_account_type: AccountType
    to_account_name: str
    recurrence_months: Optional[int] = Field(None, ge=1, le=60)
    notes: Optional[str] = None

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        return _validate_iso_date(v)


class TransferUpdate(BaseModel):
    date: Optional[str] = None
    detail: Optional[str] = None
    amount: Optional[float] = Field(None, gt=0)
    notes: Optional[str] = None

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        return _validate_iso_date(v)
