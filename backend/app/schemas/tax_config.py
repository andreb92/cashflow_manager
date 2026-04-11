from __future__ import annotations
from pydantic import BaseModel


class TaxConfigCreate(BaseModel):
    valid_from: str
    inps_rate: float = 0.0919
    irpef_band1_rate: float = 0.23
    irpef_band1_limit: float = 28000
    irpef_band2_rate: float = 0.33
    irpef_band2_limit: float = 50000
    irpef_band3_rate: float = 0.43
    employment_deduction_band1_limit: float = 15000
    employment_deduction_band1_amount: float = 1955
    employment_deduction_band2_limit: float = 28000
    employment_deduction_band2_base: float = 1910
    employment_deduction_band2_variable: float = 1190
    employment_deduction_band2_range: float = 13000
    employment_deduction_band3_limit: float = 50000
    employment_deduction_band3_base: float = 1910
    employment_deduction_band3_range: float = 22000
    pension_deductibility_cap: float = 5300.00
    employment_deduction_floor: float = 690.00
