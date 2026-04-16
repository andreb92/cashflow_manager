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


def test_compute_bank_balance_no_tracking_start_returns_zero(_standalone_db, make_user):
    """compute_bank_balance must return 0.0 when user has no tracking_start_date."""
    from app.services.bank_balance import compute_bank_balance
    user = make_user(email="nostart@test.com")
    result = compute_bank_balance(user.id, 2026, 1, _standalone_db)
    assert result == 0.0


def test_compute_bank_balance_no_mbh_rows_returns_zero(_standalone_db, make_user):
    """compute_bank_balance returns 0.0 when tracking_start_date is set but no MBH rows exist."""
    from app.services.bank_balance import compute_bank_balance
    from app.models.user import UserSetting

    user = make_user(email="nombh@test.com")
    db = _standalone_db
    db.add(UserSetting(user_id=user.id, key="tracking_start_date", value="2026-01-01"))
    db.commit()

    result = compute_bank_balance(user.id, 2026, 1, db)
    assert result == 0.0


def test_compute_bank_balance_missing_pm_is_skipped(_standalone_db, make_user):
    """compute_bank_balance skips transaction/transfer logic when MBH's PM is not found.
    The opening_balance is still applied (set before PM lookup), but subsequent months
    with a valid_from < month_first also skip since PM is still missing."""
    from app.services.bank_balance import compute_bank_balance
    from app.models.payment_method import PaymentMethod, MainBankHistory
    from app.models.user import UserSetting

    user = make_user(email="missingpm@test.com")
    db = _standalone_db
    db.add(UserSetting(user_id=user.id, key="tracking_start_date", value="2026-01-01"))
    # Real PM for Jan, deleted/missing PM for Feb (simulate by using a non-existent id in MBH)
    real_pm = PaymentMethod(user_id=user.id, name="RealBank", type="bank", is_main_bank=True)
    db.add(real_pm)
    db.flush()
    db.add(MainBankHistory(
        user_id=user.id, payment_method_id=real_pm.id,
        valid_from="2026-01-01", opening_balance=500,
    ))
    # A second MBH entry pointing to a PM that doesn't exist
    db.add(MainBankHistory(
        user_id=user.id, payment_method_id="nonexistent-pm-id",
        valid_from="2026-02-01", opening_balance=999,
    ))
    db.commit()

    # February: opening_balance resets to 999 (MBH valid_from == month_first), then PM lookup
    # fails so no transactions apply — balance is 999
    result = compute_bank_balance(user.id, 2026, 2, db)
    assert result == pytest.approx(999.0)


def test_compute_bank_balance_incoming_transfer_increases_balance(_standalone_db, make_user):
    """A transfer TO the main bank account must increase the balance."""
    from app.services.bank_balance import compute_bank_balance
    from app.models.payment_method import PaymentMethod, MainBankHistory
    from app.models.user import UserSetting
    from app.models.transfer import Transfer

    user = make_user(email="xfer_to@test.com")
    db = _standalone_db

    pm = PaymentMethod(user_id=user.id, name="MyBank", type="bank", is_main_bank=True)
    db.add(pm)
    db.flush()

    db.add(UserSetting(user_id=user.id, key="tracking_start_date", value="2026-01-01"))
    db.add(MainBankHistory(
        user_id=user.id, payment_method_id=pm.id,
        valid_from="2026-01-01", opening_balance=1000,
    ))
    # Transfer FROM savings TO main bank
    db.add(Transfer(
        user_id=user.id, date="2026-01-15", amount=500,
        from_account_type="saving", from_account_name="MySavings",
        to_account_type="bank", to_account_name="MyBank",
        billing_month="2026-01-01", detail="",
    ))
    db.commit()

    result = compute_bank_balance(user.id, 2026, 1, db)
    assert result == pytest.approx(1500.0)


def test_compute_bank_balances_for_year_no_tracking_start_returns_zeros(_standalone_db, make_user):
    """compute_bank_balances_for_year returns all zeros when no tracking_start_date."""
    from app.services.bank_balance import compute_bank_balances_for_year
    user = make_user(email="noyearstart@test.com")
    result = compute_bank_balances_for_year(user.id, 2026, _standalone_db)
    assert set(result.keys()) == set(range(1, 13))
    assert all(v == 0.0 for v in result.values())


def test_compute_bank_balances_for_year_debit_and_transfers(_standalone_db, make_user):
    """Year function covers debit, CC credit, and transfers (FROM and TO the main bank)."""
    from app.services.bank_balance import compute_bank_balances_for_year
    from app.models.payment_method import PaymentMethod, MainBankHistory
    from app.models.user import UserSetting
    from app.models.transaction import Transaction
    from app.models.transfer import Transfer
    from app.models.category import Category

    user = make_user(email="year_debit@test.com")
    db = _standalone_db

    pm = PaymentMethod(user_id=user.id, name="YearBank", type="bank", is_main_bank=True)
    cc_pm = PaymentMethod(user_id=user.id, name="MyCC", type="credit_card", is_main_bank=False)
    db.add_all([pm, cc_pm])
    db.flush()

    cat = Category(user_id=user.id, type="Housing", sub_type="Rent")
    db.add(cat)
    db.flush()

    db.add(UserSetting(user_id=user.id, key="tracking_start_date", value="2026-01-01"))
    db.add(MainBankHistory(
        user_id=user.id, payment_method_id=pm.id,
        valid_from="2026-01-01", opening_balance=2000,
    ))
    # Debit transaction on main bank in January
    db.add(Transaction(
        user_id=user.id, date="2026-01-10", detail="Rent",
        amount=400, payment_method_id=pm.id, category_id=cat.id,
        transaction_direction="debit", billing_month="2026-01-01",
    ))
    # CC credit transaction: billed in February (next-month billing for credit_card)
    db.add(Transaction(
        user_id=user.id, date="2026-01-15", detail="CC Bill",
        amount=150, payment_method_id=cc_pm.id, category_id=cat.id,
        transaction_direction="credit", billing_month="2026-02-01",
    ))
    # Transfer FROM bank in March (reduces balance)
    db.add(Transfer(
        user_id=user.id, date="2026-03-05", amount=200,
        from_account_type="bank", from_account_name="YearBank",
        to_account_type="saving", to_account_name="Savings",
        billing_month="2026-03-01", detail="",
    ))
    # Transfer TO bank in April (increases balance)
    db.add(Transfer(
        user_id=user.id, date="2026-04-10", amount=100,
        from_account_type="saving", from_account_name="Savings",
        to_account_type="bank", to_account_name="YearBank",
        billing_month="2026-04-01", detail="",
    ))
    db.commit()

    result = compute_bank_balances_for_year(user.id, 2026, db)

    assert result[1] == pytest.approx(1600.0)   # 2000 - 400
    assert result[2] == pytest.approx(1450.0)   # 1600 - 150 (CC credit)
    assert result[3] == pytest.approx(1250.0)   # 1450 - 200
    assert result[4] == pytest.approx(1350.0)   # 1250 + 100


def test_bank_balance_cc_debit_reduces_bank_in_billing_month(_standalone_db, make_user):
    """
    CC purchases (direction='debit') are billed to the next month. The bank balance
    must be reduced in billing_month, not in the transaction's date month.
    This covers the fix where debit-direction credit_card transactions were previously ignored.
    """
    from app.services.bank_balance import compute_bank_balance
    from app.models.payment_method import PaymentMethod, MainBankHistory
    from app.models.user import UserSetting
    from app.models.transaction import Transaction
    from app.models.category import Category

    user = make_user(email="cc_debit_balance@test.com")
    db = _standalone_db

    bank_pm = PaymentMethod(user_id=user.id, name="MyBank", type="bank", is_main_bank=True)
    cc_pm = PaymentMethod(user_id=user.id, name="MyCC", type="credit_card", is_main_bank=False)
    db.add_all([bank_pm, cc_pm])
    db.flush()

    cat = Category(user_id=user.id, type="Personal", sub_type="Food")
    db.add(cat)
    db.flush()

    db.add(UserSetting(user_id=user.id, key="tracking_start_date", value="2026-01-01"))
    db.add(MainBankHistory(
        user_id=user.id, payment_method_id=bank_pm.id,
        valid_from="2026-01-01", opening_balance=1000,
    ))
    # CC purchase in January — billing shifts to February
    db.add(Transaction(
        user_id=user.id, date="2026-01-20", detail="CC Purchase",
        amount=200, payment_method_id=cc_pm.id, category_id=cat.id,
        transaction_direction="debit", billing_month="2026-02-01",
    ))
    db.commit()

    # January: CC debit is billed in Feb, Jan balance is unaffected
    assert compute_bank_balance(user.id, 2026, 1, db) == pytest.approx(1000.0)
    # February: CC bill deducted from bank balance
    assert compute_bank_balance(user.id, 2026, 2, db) == pytest.approx(800.0)


def test_compute_bank_balances_for_year_cc_debit_reduces_bank_in_billing_month(_standalone_db, make_user):
    """
    Same as above but for compute_bank_balances_for_year: CC debit in Jan (billing Feb)
    must appear in the year result as a deduction in February.
    """
    from app.services.bank_balance import compute_bank_balances_for_year
    from app.models.payment_method import PaymentMethod, MainBankHistory
    from app.models.user import UserSetting
    from app.models.transaction import Transaction
    from app.models.category import Category

    user = make_user(email="cc_debit_year@test.com")
    db = _standalone_db

    bank_pm = PaymentMethod(user_id=user.id, name="MyBank", type="bank", is_main_bank=True)
    cc_pm = PaymentMethod(user_id=user.id, name="MyCC", type="credit_card", is_main_bank=False)
    db.add_all([bank_pm, cc_pm])
    db.flush()

    cat = Category(user_id=user.id, type="Personal", sub_type="Food")
    db.add(cat)
    db.flush()

    db.add(UserSetting(user_id=user.id, key="tracking_start_date", value="2026-01-01"))
    db.add(MainBankHistory(
        user_id=user.id, payment_method_id=bank_pm.id,
        valid_from="2026-01-01", opening_balance=1000,
    ))
    db.add(Transaction(
        user_id=user.id, date="2026-01-20", detail="CC Purchase",
        amount=200, payment_method_id=cc_pm.id, category_id=cat.id,
        transaction_direction="debit", billing_month="2026-02-01",
    ))
    db.commit()

    result = compute_bank_balances_for_year(user.id, 2026, db)
    assert result[1] == pytest.approx(1000.0)  # Jan unaffected
    assert result[2] == pytest.approx(800.0)   # Feb: 1000 - 200
    assert result[3] == pytest.approx(800.0)   # Mar onwards unchanged
