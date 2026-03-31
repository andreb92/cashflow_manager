from pydantic import BaseModel
from typing import Optional

class PaymentMethodCreate(BaseModel):
    name: str
    type: str
    linked_bank_id: Optional[str] = None
    opening_balance: Optional[float] = None
    has_stamp_duty: bool = False

class PaymentMethodUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    linked_bank_id: Optional[str] = None
    has_stamp_duty: Optional[bool] = None

class SetMainBankRequest(BaseModel):
    opening_balance: float
