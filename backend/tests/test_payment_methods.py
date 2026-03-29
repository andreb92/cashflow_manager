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

