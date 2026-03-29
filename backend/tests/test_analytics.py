import pytest
from tests.test_onboarding import WIZARD_PAYLOAD

def _setup(client):
    client.post("/api/v1/auth/register", json={
        "email": "alice@example.com", "password": "Password1!", "name": "Alice"
    })
    client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)
    pm_id = next(pm["id"] for pm in client.get("/api/v1/payment-methods").json() if pm["name"] == "MyBank")
    cat_id = next(c["id"] for c in client.get("/api/v1/categories").json() if c["type"] == "Housing")
    return pm_id, cat_id

def test_analytics_returns_per_category_per_month(client):
    pm_id, cat_id = _setup(client)
    client.post("/api/v1/transactions", json={
        "date": "2026-01-10", "detail": "Rent", "amount": 900,
        "payment_method_id": pm_id, "category_id": cat_id, "transaction_direction": "debit",
    })
    r = client.get("/api/v1/analytics/categories", params={"from": "2026-01", "to": "2026-01"})
    assert r.status_code == 200
    row = next((x for x in r.json() if x["type"] == "Housing"), None)
    assert row is not None
    assert row["total_amount"] == pytest.approx(900.0)

def test_analytics_direction_filter_debit_only(client):
    pm_id, cat_id = _setup(client)
    sal_cat_id = next(c["id"] for c in client.get("/api/v1/categories").json() if c["type"] == "Salary")
    client.post("/api/v1/transactions", json={
        "date": "2026-01-25", "detail": "Income", "amount": 2500,
        "payment_method_id": pm_id, "category_id": sal_cat_id, "transaction_direction": "income",
    })
    client.post("/api/v1/transactions", json={
        "date": "2026-01-10", "detail": "Rent", "amount": 900,
        "payment_method_id": pm_id, "category_id": cat_id, "transaction_direction": "debit",
    })
    r = client.get("/api/v1/analytics/categories", params={"from": "2026-01", "to": "2026-01", "direction": "debit"})
    types = {row["type"] for row in r.json()}
    assert "Salary" not in types
    assert "Housing" in types

def test_analytics_spans_multiple_months(client):
    pm_id, cat_id = _setup(client)
    for month in ["2026-01", "2026-02", "2026-03"]:
        client.post("/api/v1/transactions", json={
            "date": f"{month}-10", "detail": "Rent", "amount": 900,
            "payment_method_id": pm_id, "category_id": cat_id, "transaction_direction": "debit",
        })
    r = client.get("/api/v1/analytics/categories", params={"from": "2026-01", "to": "2026-03"})
    housing_rows = [x for x in r.json() if x["type"] == "Housing"]
    assert len(housing_rows) == 3  # one row per month

def test_analytics_no_data_returns_empty(client):
    client.post("/api/v1/auth/register", json={
        "email": "alice@example.com", "password": "Password1!", "name": "Alice"
    })
    client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)
    r = client.get("/api/v1/analytics/categories", params={"from": "2026-01", "to": "2026-12"})
    assert r.status_code == 200
    assert r.json() == []


def test_transfer_analytics_returns_saving_transfers(client):
    """Transfers to saving accounts must appear in /analytics/transfers."""
    _setup(client)
    client.post("/api/v1/transfers", json={
        "date": "2026-02-01", "detail": "Monthly saving",
        "amount": 400,
        "from_account_type": "bank", "from_account_name": "MyBank",
        "to_account_type": "saving", "to_account_name": "MySavings",
    })
    r = client.get("/api/v1/analytics/transfers", params={"from": "2026-02", "to": "2026-02"})
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["to_account_type"] == "saving"
    assert rows[0]["to_account_name"] == "MySavings"
    assert rows[0]["total_amount"] == pytest.approx(400.0)
    assert rows[0]["month"] == "2026-02"


def test_transfer_analytics_excludes_bank_to_bank(client):
    """Transfers between bank accounts must NOT appear in /analytics/transfers."""
    _setup(client)
    client.post("/api/v1/transfers", json={
        "date": "2026-02-01", "detail": "Internal move",
        "amount": 200,
        "from_account_type": "bank", "from_account_name": "MyBank",
        "to_account_type": "bank", "to_account_name": "MyBank",
    })
    r = client.get("/api/v1/analytics/transfers", params={"from": "2026-02", "to": "2026-02"})
    assert r.status_code == 200
    assert r.json() == []


def test_transfer_analytics_aggregates_multiple_transfers(client):
    """Multiple transfers to the same account in the same month must be summed."""
    _setup(client)
    for amount in [100, 200, 300]:
        client.post("/api/v1/transfers", json={
            "date": "2026-03-15", "detail": "Saving top-up",
            "amount": amount,
            "from_account_type": "bank", "from_account_name": "MyBank",
            "to_account_type": "saving", "to_account_name": "MySavings",
        })
    r = client.get("/api/v1/analytics/transfers", params={"from": "2026-03", "to": "2026-03"})
    assert r.status_code == 200
    row = next((x for x in r.json() if x["to_account_name"] == "MySavings"), None)
    assert row is not None
    assert row["total_amount"] == pytest.approx(600.0)


def test_transfer_analytics_no_data_returns_empty(client):
    _setup(client)
    r = client.get("/api/v1/analytics/transfers", params={"from": "2025-01", "to": "2025-12"})
    assert r.status_code == 200
    assert r.json() == []


def test_category_spending_aggregates_correctly(client):
    """SQL GROUP BY aggregation should sum amounts correctly."""
    pm_id, cat_id = _setup(client)
    n = 5
    for i in range(n):
        client.post("/api/v1/transactions", json={
            "date": f"2026-03-{10 + i:02d}",
            "detail": f"Expense {i}",
            "amount": 100,
            "payment_method_id": pm_id,
            "category_id": cat_id,
            "transaction_direction": "debit",
        })
    r = client.get("/api/v1/analytics/categories", params={"from": "2026-03", "to": "2026-03"})
    assert r.status_code == 200
    row = next((x for x in r.json() if x["type"] == "Housing"), None)
    assert row is not None
    assert row["total_amount"] == pytest.approx(n * 100.0)
