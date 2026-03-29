from dataclasses import dataclass


@dataclass
class SalaryBreakdown:
    gross_annual: float
    social_security: float
    pension_deductible: float
    taxable_base: float
    income_tax_gross: float
    employment_deduction: float
    income_tax_net: float
    regional_surtax: float
    municipal_surtax: float
    net_annual: float
    net_monthly: float
    meal_vouchers_monthly: float
    welfare_monthly: float


def calculate_salary(salary_cfg, tax_cfg) -> SalaryBreakdown:
    gross_annual = float(salary_cfg.ral)
    emp = float(salary_cfg.employer_contrib_rate)
    vol = float(salary_cfg.voluntary_contrib_rate)
    reg = float(salary_cfg.regional_tax_rate)
    mun = float(salary_cfg.municipal_tax_rate)
    salary_months = int(getattr(salary_cfg, "salary_months", 12))

    # Step 1 — Social security (INPS employee contribution)
    social_security = gross_annual * float(tax_cfg.inps_rate)

    # Step 2 — Pension deductible (supplementary pension contributions, employer + voluntary)
    pension_deductible = min(
        (emp + vol) * gross_annual,
        float(tax_cfg.pension_deductibility_cap),
    )

    # Step 3 — IRPEF taxable base
    taxable_base = gross_annual - social_security - pension_deductible

    # Step 4 — IRPEF gross (progressive marginal brackets)
    b1_lim = float(tax_cfg.irpef_band1_limit)
    b2_lim = float(tax_cfg.irpef_band2_limit)
    b1_r = float(tax_cfg.irpef_band1_rate)
    b2_r = float(tax_cfg.irpef_band2_rate)
    b3_r = float(tax_cfg.irpef_band3_rate)
    if taxable_base <= b1_lim:
        income_tax_gross = taxable_base * b1_r
    elif taxable_base <= b2_lim:
        income_tax_gross = b1_lim * b1_r + (taxable_base - b1_lim) * b2_r
    else:
        income_tax_gross = b1_lim * b1_r + (b2_lim - b1_lim) * b2_r + (taxable_base - b2_lim) * b3_r

    # Step 5 — Employment deduction (detrazione per lavoro dipendente)
    d1_lim = float(tax_cfg.employment_deduction_band1_limit)
    d2_lim = float(tax_cfg.employment_deduction_band2_limit)
    d3_lim = float(tax_cfg.employment_deduction_band3_limit)
    floor = float(tax_cfg.employment_deduction_floor)
    if taxable_base <= d1_lim:
        raw_deduction = float(tax_cfg.employment_deduction_band1_amount)
    elif taxable_base <= d2_lim:
        raw_deduction = (
            float(tax_cfg.employment_deduction_band2_base)
            + float(tax_cfg.employment_deduction_band2_variable)
            * (d2_lim - taxable_base)
            / float(tax_cfg.employment_deduction_band2_range)
        )
    elif taxable_base <= d3_lim:
        raw_deduction = (
            float(tax_cfg.employment_deduction_band3_base)
            * (d3_lim - taxable_base)
            / float(tax_cfg.employment_deduction_band3_range)
        )
    else:
        raw_deduction = 0.0

    # Apply legal minimum floor (only when formula yields a positive value)
    employment_deduction = max(raw_deduction, floor) if raw_deduction > 0 else 0.0

    # Step 6 — Net IRPEF
    income_tax_net = max(0.0, income_tax_gross - employment_deduction)

    # Step 7 — Regional + municipal surtax
    regional_surtax = taxable_base * reg
    municipal_surtax = taxable_base * mun

    # Step 8 — Net annual (only voluntary pension subtracted; employer cost is not employee income)
    net_annual = gross_annual - social_security - (vol * gross_annual) - income_tax_net - regional_surtax - municipal_surtax

    # Step 9 — Net monthly (divided by salary_months: 12, 13, or 14)
    net_monthly = round(net_annual / salary_months, 2)

    # Meal vouchers and welfare are paid in 12 monthly installments regardless of salary_months
    # (tredicesima/quattordicesima does not include fringe benefits in standard Italian payroll)
    meal_vouchers_monthly = float(salary_cfg.meal_vouchers_annual) / 12
    welfare_monthly = float(salary_cfg.welfare_annual) / 12

    return SalaryBreakdown(
        gross_annual=gross_annual,
        social_security=social_security,
        pension_deductible=pension_deductible,
        taxable_base=taxable_base,
        income_tax_gross=income_tax_gross,
        employment_deduction=employment_deduction,
        income_tax_net=income_tax_net,
        regional_surtax=regional_surtax,
        municipal_surtax=municipal_surtax,
        net_annual=net_annual,
        net_monthly=net_monthly,
        meal_vouchers_monthly=meal_vouchers_monthly,
        welfare_monthly=welfare_monthly,
    )
