def _setup(client):
    client.post("/api/v1/auth/register", json={
        "email": "alice@example.com", "password": "Password1!", "name": "Alice"
    })
    from tests.test_onboarding import WIZARD_PAYLOAD
    client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)

def test_list_payment_methods(client):
    _setup(client)
    r = client.get("/api/v1/payment-methods")
    assert r.status_code == 200
    assert any(pm["name"] == "MyBank" for pm in r.json())

def test_create_payment_method(client):
    _setup(client)
    r = client.post("/api/v1/payment-methods", json={"name": "MyPrepaid", "type": "prepaid"})
    assert r.status_code == 200
    assert r.json()["name"] == "MyPrepaid"

def test_rename_payment_method(client):
    _setup(client)
    pm_id = next(pm["id"] for pm in client.get("/api/v1/payment-methods").json() if pm["name"] == "MyBank")
    client.put(f"/api/v1/payment-methods/{pm_id}", json={"name": "MyBankRenamed"})
    names = [pm["name"] for pm in client.get("/api/v1/payment-methods").json()]
    assert "MyBankRenamed" in names

def test_deactivate_payment_method(client):
    _setup(client)
    pm_id = next(pm["id"] for pm in client.get("/api/v1/payment-methods").json() if pm["name"] == "MyCard")
    client.put(f"/api/v1/payment-methods/{pm_id}", json={"is_active": False})
    pm = next(m for m in client.get("/api/v1/payment-methods?active_only=false").json() if m["id"] == pm_id)
    assert pm["is_active"] is False

def test_set_main_bank_switches_flag(client):
    _setup(client)
    methods = client.get("/api/v1/payment-methods").json()
    bbva_id = next(pm["id"] for pm in methods if pm["name"] == "SecondBank")
    r = client.post(f"/api/v1/payment-methods/{bbva_id}/set-main-bank", json={"opening_balance": 2000.0})
    assert r.status_code == 200
    methods = client.get("/api/v1/payment-methods").json()
    assert not next(pm for pm in methods if pm["name"] == "MyBank")["is_main_bank"]
    assert next(pm for pm in methods if pm["name"] == "SecondBank")["is_main_bank"]

def test_set_main_bank_on_non_bank_type_returns_422(client):
    _setup(client)
    amex_id = next(pm["id"] for pm in client.get("/api/v1/payment-methods").json() if pm["name"] == "MyCard")
    r = client.post(f"/api/v1/payment-methods/{amex_id}/set-main-bank", json={"opening_balance": 0})
    assert r.status_code == 422

def test_main_bank_history_contains_two_rows_after_switch(client):
    _setup(client)
    bbva_id = next(pm["id"] for pm in client.get("/api/v1/payment-methods").json() if pm["name"] == "SecondBank")
    client.post(f"/api/v1/payment-methods/{bbva_id}/set-main-bank", json={"opening_balance": 2000.0})
    r = client.get("/api/v1/payment-methods/main-bank-history")
    assert len(r.json()) == 2


def test_active_only_excludes_inactive(client):
    _setup(client)
    # Create a payment method
    r = client.post("/api/v1/payment-methods", json={
        "name": "My Card", "type": "credit_card", "is_main_bank": False, "is_active": True,
    })
    pm_id = r.json()["id"]
    # Deactivate it
    r = client.put(f"/api/v1/payment-methods/{pm_id}", json={"is_active": False})
    assert r.status_code // 100 == 2
    # Default (active_only=true) should not include it
    r = client.get("/api/v1/payment-methods")
    names = [m["name"] for m in r.json()]
    assert "My Card" not in names
    # Explicit false should include it
    r = client.get("/api/v1/payment-methods?active_only=false")
    names = [m["name"] for m in r.json()]
    assert "My Card" in names


def test_duplicate_pm_name_returns_422(client):
    """Creating two payment methods with the same name for the same user must return 422."""
    _setup(client)
    resp1 = client.post("/api/v1/payment-methods", json={"name": "DupTest", "type": "bank"})
    assert resp1.status_code == 200
    resp2 = client.post("/api/v1/payment-methods", json={"name": "DupTest", "type": "bank"})
    assert resp2.status_code == 422


def test_stamp_duty_appears_in_monthly_summary(client):
    """Credit card with has_stamp_duty=True and spend > 77.47 → stamp_duty == 2.0 in summary."""
    client.post("/api/v1/auth/register", json={
        "email": "stamp@example.com", "password": "Password1!", "name": "Stamp"
    })
    from tests.test_onboarding import WIZARD_PAYLOAD
    client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)

    # Create a credit card with stamp duty enabled
    r = client.post("/api/v1/payment-methods", json={
        "name": "StampCard", "type": "credit_card", "has_stamp_duty": True
    })
    assert r.status_code == 200
    card_id = r.json()["id"]

    # Create a category for the transactions
    cat_r = client.post("/api/v1/categories", json={"type": "expense", "sub_type": "general"})
    assert cat_r.status_code == 200
    cat_id = cat_r.json()["id"]

    # Post two transactions on this card dated in March 2026.
    # Credit cards bill next month, so billing_month will be 2026-04-01.
    for amount in [50.00, 30.00]:
        tx_r = client.post("/api/v1/transactions", json={
            "date": "2026-03-15",
            "detail": "Purchase",
            "amount": amount,
            "payment_method_id": card_id,
            "category_id": cat_id,
            "transaction_direction": "debit",
        })
        assert tx_r.status_code == 200

    # Query the monthly summary for April 2026 (credit card billing month)
    r = client.get("/api/v1/summary/2026/4")
    assert r.status_code == 200
    data = r.json()
    assert data["stamp_duty"] == 2.0


def test_rename_collision_returns_422(client):
    """Renaming PM2 to PM1's existing name must return 422."""
    _setup(client)

    # Create two distinct payment methods
    r1 = client.post("/api/v1/payment-methods", json={"name": "Alpha", "type": "prepaid"})
    assert r1.status_code == 200

    r2 = client.post("/api/v1/payment-methods", json={"name": "Beta", "type": "prepaid"})
    assert r2.status_code == 200
    beta_id = r2.json()["id"]

    # Try to rename Beta → Alpha (collision)
    resp = client.put(f"/api/v1/payment-methods/{beta_id}", json={"name": "Alpha"})
    assert resp.status_code == 422


def test_set_main_bank_on_inactive_pm_returns_422(client):
    """set-main-bank on an inactive bank-type PM must be rejected with 422."""
    _setup(client)

    # Create a bank PM and immediately deactivate it
    r = client.post("/api/v1/payment-methods", json={"name": "InactiveBank", "type": "bank"})
    assert r.status_code == 200
    pm_id = r.json()["id"]

    client.put(f"/api/v1/payment-methods/{pm_id}", json={"is_active": False})

    # Attempt to make it main bank
    resp = client.post(f"/api/v1/payment-methods/{pm_id}/set-main-bank", json={"opening_balance": 0})
    assert resp.status_code == 422


def test_pm_rename_cascades_to_transfers(client):
    """Renaming a PM must update all Transfer rows referencing its old name."""
    from tests.test_onboarding import WIZARD_PAYLOAD

    client.post("/api/v1/auth/register", json={
        "email": "rename@test.com", "password": "Password1!", "name": "Rename"
    })
    client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)

    pms = client.get("/api/v1/payment-methods").json()
    fineco = next(pm for pm in pms if pm["name"] == "MyBank")

    # Create a transfer FROM MyBank
    client.post("/api/v1/transfers", json={
        "date": "2026-03-10", "detail": "To savings", "amount": 500,
        "from_account_type": "bank", "from_account_name": "MyBank",
        "to_account_type": "saving", "to_account_name": "My Savings",
    })

    # Rename MyBank → NewBank
    r = client.put(f"/api/v1/payment-methods/{fineco['id']}", json={"name": "NewBank"})
    assert r.status_code == 200

    # The transfer's from_account_name must now be "NewBank"
    transfers = client.get("/api/v1/transfers").json()
    assert any(t["from_account_name"] == "NewBank" for t in transfers), \
        "Transfer not updated after PM rename"
    assert not any(t["from_account_name"] == "MyBank" for t in transfers), \
        "Old PM name still present in transfers after rename"


def test_create_payment_method_invalid_type_returns_422(client):
    _setup(client)
    r = client.post("/api/v1/payment-methods", json={"name": "X", "type": "crypto"})
    assert r.status_code == 422


def test_update_payment_method_rejects_foreign_linked_bank_id(client):
    """linked_bank_id on update must belong to the current user."""
    _setup(client)
    wallet_id = client.post("/api/v1/payment-methods", json={"name": "Wallet", "type": "prepaid"}).json()["id"]

    client.post("/api/v1/auth/logout")
    client.post("/api/v1/auth/register", json={
        "email": "bob@example.com", "password": "Password1!", "name": "Bob"
    })
    from tests.test_onboarding import WIZARD_PAYLOAD
    client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)
    foreign_bank_id = next(pm["id"] for pm in client.get("/api/v1/payment-methods").json() if pm["type"] == "bank")

    client.post("/api/v1/auth/logout")
    client.post("/api/v1/auth/login", json={
        "email": "alice@example.com", "password": "Password1!"
    })
    r = client.put(f"/api/v1/payment-methods/{wallet_id}", json={"linked_bank_id": foreign_bank_id})
    assert r.status_code == 422
