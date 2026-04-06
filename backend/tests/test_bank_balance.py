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


def test_compute_bank_balances_for_year_mid_year_switch(_standalone_db, make_user):
    """compute_bank_balances_for_year uses PM1 for Jan-Jun and PM2 from Jul when main bank changes mid-year."""
    from app.services.bank_balance import compute_bank_balances_for_year
    from app.models.payment_method import PaymentMethod, MainBankHistory
    from app.models.user import UserSetting
    from app.models.transaction import Transaction
    from app.models.category import Category

    user = make_user(email="mid_year_switch@test.com")
    db = _standalone_db

    pm1 = PaymentMethod(user_id=user.id, name="BankJan", type="bank", is_main_bank=False)
    pm2 = PaymentMethod(user_id=user.id, name="BankJul", type="bank", is_main_bank=True)
    db.add_all([pm1, pm2])
    db.flush()

    # tracking starts Jan 2026
    db.add(UserSetting(user_id=user.id, key="tracking_start_date", value="2026-01-01"))

    # PM1 is main from Jan 2026 (opening 1000), PM2 from Jul 2026 (opening 5000)
    db.add(MainBankHistory(
        user_id=user.id, payment_method_id=pm1.id,
        valid_from="2026-01-01", opening_balance=1000,
    ))
    db.add(MainBankHistory(
        user_id=user.id, payment_method_id=pm2.id,
        valid_from="2026-07-01", opening_balance=5000,
    ))

    # Add a category so transactions are valid
    cat = Category(user_id=user.id, type="Salary", sub_type="Base")
    db.add(cat)
    db.flush()

    # Income on PM1 in February (should be counted toward PM1 balance)
    db.add(Transaction(
        user_id=user.id, date="2026-02-15", detail="Feb Income",
        amount=500, payment_method_id=pm1.id, category_id=cat.id,
        transaction_direction="income", billing_month="2026-02-01",
    ))
    # Income on PM2 in August (should be counted toward PM2 balance)
    db.add(Transaction(
        user_id=user.id, date="2026-08-15", detail="Aug Income",
        amount=200, payment_method_id=pm2.id, category_id=cat.id,
        transaction_direction="income", billing_month="2026-08-01",
    ))
    db.commit()

    result = compute_bank_balances_for_year(user.id, 2026, db)

    # Jan: PM1 opens at 1000, no transactions → 1000
    assert result[1] == pytest.approx(1000.0)
    # Feb: PM1 + 500 income → 1500
    assert result[2] == pytest.approx(1500.0)
    # Jun: still PM1, no more transactions → 1500
    assert result[6] == pytest.approx(1500.0)
    # Jul: PM2 opens at 5000, resets balance → 5000
    assert result[7] == pytest.approx(5000.0)
    # Aug: PM2 + 200 income → 5200
    assert result[8] == pytest.approx(5200.0)
    # Dec: no more transactions → 5200
    assert result[12] == pytest.approx(5200.0)


def test_credit_on_prepaid_does_not_reduce_bank_balance(client, db):
    """
    A 'credit' transaction on a prepaid PM must not reduce the main bank balance.
    Only credit_card and revolving PMs represent bank payoffs.
    """
    from app.services.bank_balance import compute_bank_balance

    client.post("/api/v1/auth/register", json={"email": "u@x.com", "password": "Password1!", "name": "U"})
    client.post("/api/v1/auth/login", json={"email": "u@x.com", "password": "Password1!"})

    # Onboard with a main bank
    client.post("/api/v1/onboarding", json={
        "tracking_start_date": "2026-01-01",
        "main_bank": {"name": "MainBank", "opening_balance": 1000.0},
    })

    # Add a prepaid PM
    prepaid = client.post("/api/v1/payment-methods", json={"name": "PrepaidCard", "type": "prepaid"}).json()

    # Add a 'credit' transaction on the prepaid — simulates a refund or top-up receipt
    # This should NOT deduct from the main bank balance
    client.post("/api/v1/transactions", json={
        "date": "2026-01-15",
        "detail": "Prepaid credit",
        "amount": 200,
        "payment_method_id": prepaid["id"],
        "transaction_direction": "credit",
    })

    from app.models.user import User
    user = db.query(User).filter_by(email="u@x.com").first()
    balance = compute_bank_balance(user.id, 2026, 1, db)

    # Balance should still be 1000 (no income, no bank debit)
    assert balance == pytest.approx(1000.0), (
        f"Credit on prepaid PM incorrectly reduced bank balance to {balance}"
    )


def test_credit_on_credit_card_reduces_bank_balance(client, db):
    """A 'credit' transaction on a credit_card PM must reduce the main bank balance.

    CC transactions bill the *next* month (see billing.py NEXT_MONTH_TYPES), so a
    transaction dated 2026-01-15 has billing_month 2026-02-01 and appears in February.
    """
    from app.services.bank_balance import compute_bank_balance
    client.post("/api/v1/auth/register", json={"email": "v@x.com", "password": "Password1!", "name": "V"})
    client.post("/api/v1/auth/login", json={"email": "v@x.com", "password": "Password1!"})
    client.post("/api/v1/onboarding", json={
        "tracking_start_date": "2026-01-01",
        "main_bank": {"name": "MainBank", "opening_balance": 1000.0},
    })
    cc = client.post("/api/v1/payment-methods", json={"name": "MyCreditCard", "type": "credit_card"}).json()
    client.post("/api/v1/transactions", json={
        "date": "2026-01-15",
        "detail": "CC payoff",
        "amount": 300,
        "payment_method_id": cc["id"],
        "transaction_direction": "credit",
    })
    from app.models.user import User
    user = db.query(User).filter_by(email="v@x.com").first()
    # CC billing_month is next month (Feb 2026), so check February balance
    balance = compute_bank_balance(user.id, 2026, 2, db)
    assert balance == pytest.approx(700.0), f"CC credit should reduce bank balance, got {balance}"
