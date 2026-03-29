import pytest
from tests.test_onboarding import WIZARD_PAYLOAD

def _setup(client):
    client.post("/api/v1/auth/register", json={
        "email": "alice@example.com", "password": "Password1!", "name": "Alice"
    })
    client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)

def test_assets_includes_saving_account(client):
    _setup(client)
    r = client.get("/api/v1/assets/2026")
    assert r.status_code == 200
    saving = next((a for a in r.json() if a["asset_name"] == "MySavings"), None)
    assert saving is not None
    assert saving["computed_amount"] == pytest.approx(3000.0)

def test_assets_saving_grows_with_transfer(client):
    _setup(client)
    client.post("/api/v1/transfers", json={
        "date": "2026-03-01", "amount": 500,
        "from_account_type": "bank", "from_account_name": "MyBank",
        "to_account_type": "saving", "to_account_name": "MySavings",
    })
    r = client.get("/api/v1/assets/2026")
    caab = next(a for a in r.json() if a["asset_name"] == "MySavings")
    assert caab["computed_amount"] == pytest.approx(3500.0)

def test_assets_investment_computed_correctly(client):
    _setup(client)
    r = client.get("/api/v1/assets/2026")
    directa = next(a for a in r.json() if a["asset_name"] == "MyBroker")
    assert directa["computed_amount"] == pytest.approx(8000.0)

def test_manual_override_replaces_computed(client):
    _setup(client)
    r = client.put("/api/v1/assets/2026/saving/MySavings", json={"manual_override": 9999.0})
    assert r.status_code == 200
    r2 = client.get("/api/v1/assets/2026")
    caab = next(a for a in r2.json() if a["asset_name"] == "MySavings")
    assert caab["final_amount"] == pytest.approx(9999.0)
    assert caab["computed_amount"] == pytest.approx(3000.0)

def test_final_amount_falls_back_to_computed_without_override(client):
    _setup(client)
    r = client.get("/api/v1/assets/2026")
    caab = next(a for a in r.json() if a["asset_name"] == "MySavings")
    assert caab["final_amount"] == caab["computed_amount"]


def test_pension_month_count_uses_relativedelta(_standalone_db, make_user):
    """Pension months must be counted correctly across year boundaries."""
    from app.services.assets import compute_assets
    from app.models.salary import SalaryConfig
    from app.models.user import UserSetting

    user = make_user(email="pension@test.com")
    db = _standalone_db

    # Salary valid from 2025-07-01 — contributes for 6 months of 2025
    db.add(SalaryConfig(
        user_id=user.id, valid_from="2025-07-01", ral=36000,
        employer_contrib_rate=0.0693, voluntary_contrib_rate=0.02,
        regional_tax_rate=0.0123, municipal_tax_rate=0.008,
        meal_vouchers_annual=0, welfare_annual=0,
        salary_months=12, computed_net_monthly=0,
    ))
    db.add(UserSetting(user_id=user.id, key="tracking_start_date", value="2025-01-01"))
    db.commit()

    rows = compute_assets(user.id, 2025, db)
    pension_rows = [r for r in rows if r.asset_type == "pension"]
    assert len(pension_rows) == 1
    # 6 months (Jul–Dec), rate=0.0693+0.02=0.0893, ral=36000
    expected = round(0.0893 * 36000 * 6 / 12, 2)
    assert abs(pension_rows[0].computed_amount - expected) < 0.01


def test_assets_transfer_balance_multiple_accounts(_standalone_db, make_user):
    """compute_assets must correctly aggregate transfers across multiple saving accounts."""
    from app.services.assets import compute_assets
    from app.models.user import UserSetting
    from app.models.transfer import Transfer

    user = make_user(email="multi_asset@test.com")
    db = _standalone_db

    db.add(UserSetting(user_id=user.id, key="tracking_start_date", value="2026-01-01"))
    db.add(UserSetting(user_id=user.id, key="opening_saving_balance_Alpha", value="1000"))
    db.add(UserSetting(user_id=user.id, key="opening_saving_balance_Beta", value="500"))

    db.add(Transfer(
        user_id=user.id, date="2026-03-01", detail="deposit",
        amount=200, from_account_type="bank", from_account_name="Main",
        to_account_type="saving", to_account_name="Alpha",
        billing_month="2026-03-01",
    ))
    db.add(Transfer(
        user_id=user.id, date="2026-06-01", detail="withdraw",
        amount=100, from_account_type="saving", from_account_name="Beta",
        to_account_type="bank", to_account_name="Main",
        billing_month="2026-06-01",
    ))
    db.commit()

    rows = compute_assets(user.id, 2026, db)
    alpha = next(r for r in rows if r.asset_name == "Alpha")
    beta = next(r for r in rows if r.asset_name == "Beta")
    assert alpha.computed_amount == 1200.0   # 1000 + 200 in
    assert beta.computed_amount == 400.0     # 500 - 100 out
