import pytest
from tests.test_onboarding import WIZARD_PAYLOAD

def _setup(client, db):
    client.post("/api/v1/auth/register", json={
        "email": "alice@example.com", "password": "Password1!", "name": "Alice"
    })
    client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)
    from app.models.user import User
    return db.query(User).filter_by(email="alice@example.com").first()

def test_bank_balance_equals_opening_for_empty_month(client, db):
    user = _setup(client, db)
    from app.services.bank_balance import compute_bank_balance
    balance = compute_bank_balance(user.id, 2026, 1, db)
    assert balance == pytest.approx(5000.0)

def test_bank_balance_increases_with_income(client, db):
    user = _setup(client, db)
    pm_id = next(pm["id"] for pm in client.get("/api/v1/payment-methods").json() if pm["name"] == "MyBank")
    cat_id = next(c["id"] for c in client.get("/api/v1/categories").json() if c["type"] == "Salary")
    client.post("/api/v1/transactions", json={
        "date": "2026-01-25", "detail": "Salary Jan",
        "amount": 2500, "payment_method_id": pm_id,
        "category_id": cat_id, "transaction_direction": "income",
    })
    from app.services.bank_balance import compute_bank_balance
    balance = compute_bank_balance(user.id, 2026, 1, db)
    assert balance == pytest.approx(7500.0)

def test_bank_balance_decreases_with_debit(client, db):
    user = _setup(client, db)
    pm_id = next(pm["id"] for pm in client.get("/api/v1/payment-methods").json() if pm["name"] == "MyBank")
    cat_id = next(c["id"] for c in client.get("/api/v1/categories").json() if c["type"] == "Housing")
    client.post("/api/v1/transactions", json={
        "date": "2026-01-05", "detail": "Rent",
        "amount": 900, "payment_method_id": pm_id,
        "category_id": cat_id, "transaction_direction": "debit",
    })
    from app.services.bank_balance import compute_bank_balance
    balance = compute_bank_balance(user.id, 2026, 1, db)
    assert balance == pytest.approx(4100.0)

def test_bank_balance_decreases_with_outgoing_transfer(client, db):
    user = _setup(client, db)
    client.post("/api/v1/transfers", json={
        "date": "2026-01-15", "amount": 300,
        "from_account_type": "bank", "from_account_name": "MyBank",
        "to_account_type": "saving", "to_account_name": "MySavings",
    })
    from app.services.bank_balance import compute_bank_balance
    balance = compute_bank_balance(user.id, 2026, 1, db)
    assert balance == pytest.approx(4700.0)

def test_bank_balance_carries_over_to_next_month(client, db):
    user = _setup(client, db)
    pm_id = next(pm["id"] for pm in client.get("/api/v1/payment-methods").json() if pm["name"] == "MyBank")
    cat_id = next(c["id"] for c in client.get("/api/v1/categories").json() if c["type"] == "Salary")
    client.post("/api/v1/transactions", json={
        "date": "2026-01-25", "detail": "Salary Jan",
        "amount": 2500, "payment_method_id": pm_id,
        "category_id": cat_id, "transaction_direction": "income",
    })
    from app.services.bank_balance import compute_bank_balance
    balance_feb = compute_bank_balance(user.id, 2026, 2, db)
    # No Feb transactions → balance carries from Jan: 5000 + 2500 = 7500
    assert balance_feb == pytest.approx(7500.0)


def test_bank_balance_with_main_bank_change(_standalone_db, make_user):
    """Balance is correct when main bank switches mid-year."""
    from app.services.bank_balance import compute_bank_balance
    from app.models.payment_method import PaymentMethod, MainBankHistory
    from app.models.user import UserSetting

    user = make_user(email="mbh_change@test.com")
    db = _standalone_db

    pm1 = PaymentMethod(user_id=user.id, name="BankA", type="bank", is_main_bank=False)
    pm2 = PaymentMethod(user_id=user.id, name="BankB", type="bank", is_main_bank=True)
    db.add_all([pm1, pm2])
    db.flush()

    db.add(UserSetting(user_id=user.id, key="tracking_start_date", value="2026-01-01"))
    # BankA is main from Jan, BankB from Apr
    db.add(MainBankHistory(user_id=user.id, payment_method_id=pm1.id,
                           valid_from="2026-01-01", opening_balance=1000))
    db.add(MainBankHistory(user_id=user.id, payment_method_id=pm2.id,
                           valid_from="2026-04-01", opening_balance=2000))
    db.commit()

    # Balance in March uses BankA (1000 opening, no transactions)
    bal_mar = compute_bank_balance(user.id, 2026, 3, db)
    assert bal_mar == 1000.0

    # Balance in April uses BankB (2000 opening)
    bal_apr = compute_bank_balance(user.id, 2026, 4, db)
    assert bal_apr == 2000.0
