from pydantic import BaseModel
from typing import Optional, List

class MainBankIn(BaseModel):
    name: str
    opening_balance: float = 0.0

class AdditionalBankIn(BaseModel):
    name: str
    opening_balance: float = 0.0

class PaymentMethodIn(BaseModel):
    name: str
    type: str
    linked_bank_name: Optional[str] = None
    opening_balance: Optional[float] = None

class SavingAccountIn(BaseModel):
    name: str
    opening_balance: float = 0.0

class InvestmentAccountIn(BaseModel):
    name: str
    opening_balance: float = 0.0

class SalaryIn(BaseModel):
    ral: float
    employer_contrib_rate: float = 0.0
    voluntary_contrib_rate: float = 0.0
    regional_tax_rate: float = 0.0
    municipal_tax_rate: float = 0.0
    meal_vouchers_annual: float = 0.0
    welfare_annual: float = 0.0
    salary_months: int = 12
    manual_net_override: Optional[float] = None

class OnboardingPayload(BaseModel):
    tracking_start_date: str
    main_bank: MainBankIn
    additional_banks: List[AdditionalBankIn] = []
    payment_methods: List[PaymentMethodIn] = []
    saving_accounts: List[SavingAccountIn] = []
    investment_accounts: List[InvestmentAccountIn] = []
    salary: Optional[SalaryIn] = None
