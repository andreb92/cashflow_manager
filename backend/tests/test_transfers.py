from tests.test_onboarding import WIZARD_PAYLOAD

def _setup(client):
    client.post("/api/v1/auth/register", json={
        "email": "alice@example.com", "password": "Password1!", "name": "Alice"
    })
    client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)

def test_create_transfer(client):
    _setup(client)
    r = client.post("/api/v1/transfers", json={
        "date": "2026-03-15", "detail": "Monthly savings",
        "amount": 500, "from_account_type": "bank",
        "from_account_name": "MyBank", "to_account_type": "saving",
        "to_account_name": "MySavings",
    })
    assert r.status_code == 200
    assert r.json()["billing_month"] == "2026-03-01"

def test_transfer_billing_month_is_always_current_month(client):
    # Transfers always use current month regardless of account type
    _setup(client)
    r = client.post("/api/v1/transfers", json={
        "date": "2026-12-20", "amount": 100,
        "from_account_type": "bank", "from_account_name": "MyBank",
        "to_account_type": "saving", "to_account_name": "MySavings",
    })
    assert r.json()["billing_month"] == "2026-12-01"

def test_create_recurring_transfer(client):
    _setup(client)
    client.post("/api/v1/transfers", json={
        "date": "2026-01-01", "amount": 200,
        "from_account_type": "bank", "from_account_name": "MyBank",
        "to_account_type": "saving", "to_account_name": "MySavings",
        "recurrence_months": 3,
    })
    transfers = client.get("/api/v1/transfers").json()
    assert len([t for t in transfers if t["from_account_name"] == "MyBank"]) == 3

def test_delete_single_transfer(client):
    _setup(client)
    tx_id = client.post("/api/v1/transfers", json={
        "date": "2026-03-01", "amount": 100,
        "from_account_type": "bank", "from_account_name": "MyBank",
        "to_account_type": "saving", "to_account_name": "MySavings",
    }).json()["id"]
    assert client.delete(f"/api/v1/transfers/{tx_id}", params={"cascade": "single"}).status_code == 200
    assert client.get(f"/api/v1/transfers/{tx_id}").status_code == 404


def test_list_transfers_filter_by_billing_month(client):
    _setup(client)
    client.post("/api/v1/transfers", json={
        "date": "2026-03-01", "amount": 100,
        "from_account_type": "bank", "from_account_name": "MyBank",
        "to_account_type": "saving", "to_account_name": "MySavings",
    })
    client.post("/api/v1/transfers", json={
        "date": "2026-05-01", "amount": 200,
        "from_account_type": "bank", "from_account_name": "MyBank",
        "to_account_type": "saving", "to_account_name": "MySavings",
    })
    r = client.get("/api/v1/transfers", params={"billing_month": "2026-03"})
    assert r.status_code == 200
    results = r.json()
    assert len(results) == 1
    assert results[0]["billing_month"].startswith("2026-03")


def test_list_transfers_filter_by_from_account(client):
    _setup(client)
    client.post("/api/v1/transfers", json={
        "date": "2026-03-01", "amount": 100,
        "from_account_type": "bank", "from_account_name": "MyBank",
        "to_account_type": "saving", "to_account_name": "MySavings",
    })
    r = client.get("/api/v1/transfers", params={"from_account": "MyBank"})
    assert r.status_code == 200
    assert all(t["from_account_name"] == "MyBank" for t in r.json())


def test_list_transfers_filter_by_to_account(client):
    _setup(client)
    client.post("/api/v1/transfers", json={
        "date": "2026-03-01", "amount": 100,
        "from_account_type": "bank", "from_account_name": "MyBank",
        "to_account_type": "saving", "to_account_name": "MySavings",
    })
    r = client.get("/api/v1/transfers", params={"to_account": "MySavings"})
    assert r.status_code == 200
    assert all(t["to_account_name"] == "MySavings" for t in r.json())


def test_get_transfer_not_found(client):
    _setup(client)
    r = client.get("/api/v1/transfers/nonexistent-id")
    assert r.status_code == 404


def test_update_transfer_cascade_single(client):
    _setup(client)
    first_id = client.post("/api/v1/transfers", json={
        "date": "2026-01-01", "amount": 200, "detail": "Original",
        "from_account_type": "bank", "from_account_name": "MyBank",
        "to_account_type": "saving", "to_account_name": "MySavings",
        "recurrence_months": 3,
    }).json()["id"]
    all_transfers = client.get("/api/v1/transfers").json()
    second = next(t for t in all_transfers if t["id"] != first_id and t["parent_transfer_id"] == first_id and t["date"].startswith("2026-02"))
    # Update only the second occurrence
    r = client.put(f"/api/v1/transfers/{second['id']}", json={"amount": 999.0}, params={"cascade": "single"})
    assert r.status_code == 200
    updated = client.get(f"/api/v1/transfers/{second['id']}").json()
    assert updated["amount"] == 999.0
    # First occurrence should be unchanged
    first = client.get(f"/api/v1/transfers/{first_id}").json()
    assert first["amount"] == 200.0


def test_update_transfer_cascade_all(client):
    _setup(client)
    first_id = client.post("/api/v1/transfers", json={
        "date": "2026-01-01", "amount": 200, "detail": "Recurrent",
        "from_account_type": "bank", "from_account_name": "MyBank",
        "to_account_type": "saving", "to_account_name": "MySavings",
        "recurrence_months": 3,
    }).json()["id"]
    second_id = next(
        t["id"] for t in client.get("/api/v1/transfers").json()
        if t["id"] != first_id and t["parent_transfer_id"] == first_id
    )
    r = client.put(f"/api/v1/transfers/{second_id}", json={"amount": 777.0}, params={"cascade": "all"})
    assert r.status_code == 200
    all_amounts = [t["amount"] for t in client.get("/api/v1/transfers").json()]
    assert all(a == 777.0 for a in all_amounts)


def test_update_transfer_cascade_future(client):
    _setup(client)
    first_id = client.post("/api/v1/transfers", json={
        "date": "2026-01-01", "amount": 200, "detail": "Recurrent",
        "from_account_type": "bank", "from_account_name": "MyBank",
        "to_account_type": "saving", "to_account_name": "MySavings",
        "recurrence_months": 3,
    }).json()["id"]
    all_transfers = client.get("/api/v1/transfers").json()
    second = next(t for t in all_transfers if t["id"] != first_id and t["parent_transfer_id"] == first_id and t["date"].startswith("2026-02"))
    r = client.put(f"/api/v1/transfers/{second['id']}", json={"amount": 555.0}, params={"cascade": "future"})
    assert r.status_code == 200
    # First occurrence (before the updated one) should remain unchanged
    first = client.get(f"/api/v1/transfers/{first_id}").json()
    assert first["amount"] == 200.0
    # The updated and later occurrences should be 555
    updated = client.get(f"/api/v1/transfers/{second['id']}").json()
    assert updated["amount"] == 555.0


def test_delete_transfer_cascade_all(client):
    _setup(client)
    first_id = client.post("/api/v1/transfers", json={
        "date": "2026-01-01", "amount": 200,
        "from_account_type": "bank", "from_account_name": "MyBank",
        "to_account_type": "saving", "to_account_name": "MySavings",
        "recurrence_months": 3,
    }).json()["id"]
    r = client.delete(f"/api/v1/transfers/{first_id}", params={"cascade": "all"})
    assert r.status_code == 200
    remaining = client.get("/api/v1/transfers").json()
    assert len(remaining) == 0


def test_delete_transfer_cascade_future(client):
    _setup(client)
    first_id = client.post("/api/v1/transfers", json={
        "date": "2026-01-01", "amount": 200,
        "from_account_type": "bank", "from_account_name": "MyBank",
        "to_account_type": "saving", "to_account_name": "MySavings",
        "recurrence_months": 3,
    }).json()["id"]
    all_transfers = client.get("/api/v1/transfers").json()
    second = next(t for t in all_transfers if t["id"] != first_id and t["parent_transfer_id"] == first_id and t["date"].startswith("2026-02"))
    r = client.delete(f"/api/v1/transfers/{second['id']}", params={"cascade": "future"})
    assert r.status_code == 200
    # Only the first occurrence should remain
    remaining = client.get("/api/v1/transfers").json()
    assert len(remaining) == 1
    assert remaining[0]["id"] == first_id
