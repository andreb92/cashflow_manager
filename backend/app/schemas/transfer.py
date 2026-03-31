from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


class TransferCreate(BaseModel):
    date: str
    detail: str = ""
    amount: float = Field(gt=0)
    from_account_type: str
    from_account_name: str
    to_account_type: str
    to_account_name: str
    recurrence_months: Optional[int] = None
    notes: Optional[str] = None


class TransferUpdate(BaseModel):
    date: Optional[str] = None
    detail: Optional[str] = None
    amount: Optional[float] = Field(None, gt=0)
    notes: Optional[str] = None
