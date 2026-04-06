from dataclasses import dataclass
from typing import Optional, List
from sqlalchemy.orm import Session
from dateutil.parser import parse as _p
from dateutil.relativedelta import relativedelta as _rdelta
from app.models.user import UserSetting
from app.models.transfer import Transfer
from app.models.asset import Asset
from app.models.salary import SalaryConfig

@dataclass
class AssetRow:
    asset_type: str          # saving | investment | bank | pension
    asset_name: str
    computed_amount: float
    manual_override: Optional[float]
    final_amount: float

def _get_settings(db, user_id) -> dict:
    rows = db.query(UserSetting).filter_by(user_id=user_id).all()
    return {r.key: r.value for r in rows}

def compute_assets(user_id: str, year: int, db: Session) -> List[AssetRow]:
    settings = _get_settings(db, user_id)
    # Manual overrides for this year
    overrides = {
        (a.asset_type, a.asset_name): a.manual_override
        for a in db.query(Asset).filter_by(user_id=user_id, year=year).all()
    }

    rows: List[AssetRow] = []

    def _make_row(asset_type, name, computed):
        override = overrides.get((asset_type, name))
        return AssetRow(
            asset_type=asset_type, asset_name=name,
            computed_amount=computed,
            manual_override=override,
            final_amount=override if override is not None else computed,
        )

    # Bulk-load all transfers for this year once
    year_start = f"{year:04d}-01-01"
    year_end = f"{year:04d}-12-31"
    year_transfers = (
        db.query(Transfer)
        .filter_by(user_id=user_id)
        .filter(Transfer.billing_month >= year_start, Transfer.billing_month <= year_end)
        .all()
    )
    from collections import defaultdict
    transfers_in: dict = defaultdict(float)
    transfers_out: dict = defaultdict(float)
    for t in year_transfers:
        transfers_in[t.to_account_name] += float(t.amount)
        transfers_out[t.from_account_name] += float(t.amount)

    def _transfer_balance(opening: float, account_name: str) -> float:
        return opening + transfers_in.get(account_name, 0.0) - transfers_out.get(account_name, 0.0)

    # Saving accounts
    for key, value in settings.items():
        if key.startswith("opening_saving_balance_"):
            name = key[len("opening_saving_balance_"):]
            rows.append(_make_row("saving", name, _transfer_balance(float(value), name)))

    # Investment accounts
    for key, value in settings.items():
        if key.startswith("opening_investment_balance_"):
            name = key[len("opening_investment_balance_"):]
            rows.append(_make_row("investment", name, _transfer_balance(float(value), name)))

    # Pension (employer + voluntary contrib × RAL × months_elapsed / 12)
    salary_cfgs = (
        db.query(SalaryConfig)
        .filter_by(user_id=user_id)
        .order_by(SalaryConfig.valid_from)
        .all()
    )
    pension_total = 0.0
    year_start = f"{year:04d}-01-01"
    next_year_start = f"{year + 1:04d}-01-01"
    for i, sc in enumerate(salary_cfgs):
        period_start = sc.valid_from
        period_end = salary_cfgs[i + 1].valid_from if i + 1 < len(salary_cfgs) else next_year_start
        active_start = max(period_start, year_start)
        active_end = min(period_end, next_year_start)
        if active_start >= active_end:
            continue
        rd = _rdelta(_p(active_end), _p(active_start))
        months_active = rd.years * 12 + rd.months + (1 if rd.days >= 15 else 0)
        ral = float(sc.ral)
        rate = float(sc.employer_contrib_rate) + float(sc.voluntary_contrib_rate)
        pension_total += rate * ral * months_active / 12
    if pension_total > 0:
        rows.append(_make_row("pension", "Pension", round(pension_total, 2)))

    return rows
