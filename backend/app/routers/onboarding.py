from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.deps import get_db, get_current_user
from app.models.user import User, UserSetting
from app.models.payment_method import PaymentMethod, MainBankHistory
from app.models.category import Category
from app.models.salary import SalaryConfig
from app.models.transaction import Transaction
from app.models.transfer import Transfer
from app.schemas.onboarding import OnboardingPayload
from app.services.seed import DEFAULT_CATEGORIES
from app.services.salary import calculate_salary
from app.services.tax import resolve_tax_config

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

def _set_setting(db, user_id, key, value):
    row = db.query(UserSetting).filter_by(user_id=user_id, key=key).first()
    if row:
        row.value = str(value)
    else:
        db.add(UserSetting(user_id=user_id, key=key, value=str(value)))

def _get_setting(db, user_id, key):
    row = db.query(UserSetting).filter_by(user_id=user_id, key=key).first()
    return row.value if row else None

@router.get("/status")
def onboarding_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    complete = _get_setting(db, current_user.id, "onboarding_complete") == "true"
    return {"complete": complete}

@router.post("")
def submit_onboarding(
    payload: OnboardingPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Idempotent — wipe and recreate per-user setup data
    # Delete FK children before parents: MainBankHistory.payment_method_id → payment_methods.id
    db.query(Transaction).filter(Transaction.user_id == current_user.id).delete()
    db.query(Transfer).filter(Transfer.user_id == current_user.id).delete()
    db.query(MainBankHistory).filter_by(user_id=current_user.id).delete()
    db.query(PaymentMethod).filter_by(user_id=current_user.id).delete()
    db.query(Category).filter_by(user_id=current_user.id).delete()
    db.query(SalaryConfig).filter_by(user_id=current_user.id).delete()
    db.query(UserSetting).filter_by(user_id=current_user.id).delete()
    db.flush()

    _set_setting(db, current_user.id, "tracking_start_date", payload.tracking_start_date)

    # Main bank
    main_pm = PaymentMethod(
        user_id=current_user.id, name=payload.main_bank.name,
        type="bank", is_main_bank=True,
    )
    db.add(main_pm)
    db.flush()
    _set_setting(db, current_user.id, f"opening_bank_balance_{main_pm.id}", payload.main_bank.opening_balance)
    db.add(MainBankHistory(
        user_id=current_user.id, payment_method_id=main_pm.id,
        valid_from=payload.tracking_start_date, opening_balance=payload.main_bank.opening_balance,
    ))

    # Additional banks
    bank_name_to_id = {payload.main_bank.name: main_pm.id}
    for ab in (payload.additional_banks or []):
        pm = PaymentMethod(user_id=current_user.id, name=ab.name, type="bank")
        db.add(pm)
        db.flush()
        bank_name_to_id[ab.name] = pm.id
        _set_setting(db, current_user.id, f"opening_bank_balance_{pm.id}", ab.opening_balance)

    # Other payment methods
    for pmi in (payload.payment_methods or []):
        linked_id = bank_name_to_id.get(pmi.linked_bank_name) if pmi.linked_bank_name else None
        pm = PaymentMethod(
            user_id=current_user.id, name=pmi.name, type=pmi.type,
            linked_bank_id=linked_id, opening_balance=pmi.opening_balance,
        )
        db.add(pm)
        db.flush()
        if pmi.type == "prepaid" and pmi.opening_balance is not None:
            _set_setting(db, current_user.id, f"opening_bank_balance_{pm.id}", pmi.opening_balance)

    # Saving / investment accounts
    for sa in (payload.saving_accounts or []):
        _set_setting(db, current_user.id, f"opening_saving_balance_{sa.name}", sa.opening_balance)
    for ia in (payload.investment_accounts or []):
        _set_setting(db, current_user.id, f"opening_investment_balance_{ia.name}", ia.opening_balance)

    # Default categories (Saving/* start inactive — tracked via Transfers)
    for type_, sub_type in DEFAULT_CATEGORIES:
        db.add(Category(
            user_id=current_user.id, type=type_, sub_type=sub_type,
            is_active=(type_ != "Saving"),
        ))

    # Salary (optional)
    if payload.salary:
        tax_cfg = resolve_tax_config(db, payload.tracking_start_date[:7], current_user.id)
        breakdown = calculate_salary(payload.salary, tax_cfg) if tax_cfg else None
        db.add(SalaryConfig(
            user_id=current_user.id,
            valid_from=payload.tracking_start_date,
            ral=payload.salary.ral,
            employer_contrib_rate=payload.salary.employer_contrib_rate,
            voluntary_contrib_rate=payload.salary.voluntary_contrib_rate,
            regional_tax_rate=payload.salary.regional_tax_rate,
            municipal_tax_rate=payload.salary.municipal_tax_rate,
            meal_vouchers_annual=payload.salary.meal_vouchers_annual,
            welfare_annual=payload.salary.welfare_annual,
            salary_months=payload.salary.salary_months,
            manual_net_override=payload.salary.manual_net_override,
            computed_net_monthly=breakdown.net_monthly if breakdown else 0,
        ))

    _set_setting(db, current_user.id, "onboarding_complete", "true")
    db.commit()
    return {"ok": True}
