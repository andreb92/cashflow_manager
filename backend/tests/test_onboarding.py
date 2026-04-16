import pytest

WIZARD_PAYLOAD = {
    "tracking_start_date": "2026-01-01",
    "main_bank": {"name": "MyBank", "opening_balance": 5000.00},
    "additional_banks": [{"name": "SecondBank", "opening_balance": 1200.00}],
    "payment_methods": [
        {"name": "MyCard", "type": "credit_card"},
        {"name": "MyBank Debit", "type": "debit_card", "linked_bank_name": "MyBank"},
    ],
    "saving_accounts": [{"name": "MySavings", "opening_balance": 3000.00}],
    "investment_accounts": [{"name": "MyBroker", "opening_balance": 8000.00}],
    "salary": {
        "ral": 42000,
        "employer_contrib_rate": 0.04,
        "voluntary_contrib_rate": 0.02,
        "regional_tax_rate": 0.0173,
        "municipal_tax_rate": 0.008,
        "meal_vouchers_annual": 1200,
        "welfare_annual": 500,
    },
}

def test_onboarding_status_incomplete_for_new_user(client):
    client.post("/api/v1/auth/register", json={
        "email": "alice@example.com", "password": "Password1!", "name": "Alice"
    })
    r = client.get("/api/v1/onboarding/status")
    assert r.status_code == 200
    assert r.json()["complete"] is False

def test_onboarding_submit_sets_complete(client):
    client.post("/api/v1/auth/register", json={
        "email": "alice@example.com", "password": "Password1!", "name": "Alice"
    })
    r = client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)
    assert r.status_code == 200
    r2 = client.get("/api/v1/onboarding/status")
    assert r2.json()["complete"] is True

def test_onboarding_creates_payment_methods(client, db):
    client.post("/api/v1/auth/register", json={
        "email": "alice@example.com", "password": "Password1!", "name": "Alice"
    })
    client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)
    from app.models.payment_method import PaymentMethod
    methods = db.query(PaymentMethod).all()
    names = {m.name for m in methods}
    assert "MyBank" in names
    assert "SecondBank" in names
    assert "MyCard" in names

def test_onboarding_creates_main_bank_history(client, db):
    client.post("/api/v1/auth/register", json={
        "email": "alice@example.com", "password": "Password1!", "name": "Alice"
    })
    client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)
    from app.models.payment_method import MainBankHistory
    history = db.query(MainBankHistory).all()
    assert len(history) == 1
    assert float(history[0].opening_balance) == pytest.approx(5000.00)
    assert history[0].valid_from == "2026-01-01"

def test_onboarding_stores_opening_balances_in_user_settings(client, db):
    client.post("/api/v1/auth/register", json={
        "email": "alice@example.com", "password": "Password1!", "name": "Alice"
    })
    client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)
    from app.models.user import UserSetting
    settings = {s.key: s.value for s in db.query(UserSetting).all()}
    assert settings.get("tracking_start_date") == "2026-01-01"
    assert settings.get("opening_saving_balance_MySavings") == "3000.0"
    assert settings.get("opening_investment_balance_MyBroker") == "8000.0"

def test_onboarding_seeds_default_categories(client, db):
    client.post("/api/v1/auth/register", json={
        "email": "alice@example.com", "password": "Password1!", "name": "Alice"
    })
    client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)
    from app.models.category import Category
    cats = db.query(Category).all()
    assert len(cats) > 0
    types = {c.type for c in cats}
    assert "Housing" in types
    assert "Salary" in types
    assert "Bills" not in types, "Bills must not be a top-level category type"

def test_onboarding_idempotent_returns_200(client):
    client.post("/api/v1/auth/register", json={
        "email": "alice@example.com", "password": "Password1!", "name": "Alice"
    })
    client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)
    r2 = client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)
    assert r2.status_code == 200

def test_re_onboarding_cleans_up_main_bank_history(client, db):
    """Re-submitting onboarding must not leave orphaned MainBankHistory rows."""
    from app.models.payment_method import MainBankHistory, PaymentMethod

    client.post("/api/v1/auth/register", json={
        "email": "reob@example.com", "password": "Password1!", "name": "ReOb"
    })
    r1 = client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)
    assert r1.status_code == 200

    r2 = client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)
    assert r2.status_code == 200

    # All MainBankHistory rows must reference an existing PaymentMethod
    orphans = (
        db.query(MainBankHistory)
        .outerjoin(PaymentMethod, MainBankHistory.payment_method_id == PaymentMethod.id)
        .filter(PaymentMethod.id.is_(None))
        .count()
    )
    assert orphans == 0, f"Found {orphans} orphaned MainBankHistory rows after re-onboarding"


def test_resubmit_onboarding_deletes_transactions_and_transfers(client, db):
    """Re-submitting onboarding must wipe existing Transaction and Transfer rows."""
    from app.models.transaction import Transaction
    from app.models.transfer import Transfer

    client.post("/api/v1/auth/register", json={
        "email": "resubmit@example.com", "password": "Password1!", "name": "Resubmit"
    })
    r1 = client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)
    assert r1.status_code == 200

    # Fetch the main bank payment method id so we can create a transaction
    from app.models.payment_method import PaymentMethod
    db.expire_all()
    main_pm = db.query(PaymentMethod).filter_by(name="MyBank").first()
    assert main_pm is not None

    # Directly insert a Transaction row to simulate existing data
    from app.models.user import User
    user = db.query(User).filter_by(email="resubmit@example.com").first()
    txn = Transaction(
        user_id=user.id,
        date="2026-01-15",
        detail="Test expense",
        amount=100.0,
        payment_method_id=main_pm.id,
        transaction_direction="debit",
        billing_month="2026-01",
    )
    db.add(txn)
    db.commit()

    assert db.query(Transaction).filter_by(user_id=user.id).count() == 1

    # Re-submit onboarding
    r2 = client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)
    assert r2.status_code == 200

    db.expire_all()
    assert db.query(Transaction).filter_by(user_id=user.id).count() == 0
    assert db.query(Transfer).filter_by(user_id=user.id).count() == 0


def test_onboarding_salary_months_stored(client):
    client.post("/api/v1/auth/register", json={
        "email": "bob@example.com", "password": "Password1!", "name": "Bob"
    })
    payload = {
        "tracking_start_date": "2026-01-01",
        "main_bank": {"name": "MyBank", "opening_balance": 5000},
        "salary": {
            "ral": 42000,
            "employer_contrib_rate": 0.04,
            "voluntary_contrib_rate": 0.0,
            "regional_tax_rate": 0.0173,
            "municipal_tax_rate": 0.001,
            "meal_vouchers_annual": 0,
            "welfare_annual": 0,
            "salary_months": 13,
        },
    }
    r = client.post("/api/v1/onboarding", json=payload)
    assert r.status_code == 200
    configs = client.get("/api/v1/salary").json()
    assert len(configs) == 1
    assert configs[0]["salary_months"] == 13
