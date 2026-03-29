import pytest
from tests.test_onboarding import WIZARD_PAYLOAD

def _setup(client):
    client.post("/api/v1/auth/register", json={
        "email": "alice@example.com", "password": "Password1!", "name": "Alice"
    })
    client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)

def test_summary_year_returns_12_months(client):
    _setup(client)
    r = client.get("/api/v1/summary/2026")
    assert r.status_code == 200
    assert len(r.json()) == 12

def test_summary_month_contains_bank_balance(client):
    _setup(client)
    r = client.get("/api/v1/summary/2026/1")
    assert r.status_code == 200
    data = r.json()
    assert "bank_balance" in data
    assert data["bank_balance"] == pytest.approx(5000.0)

def test_summary_month_shows_income_and_outcomes(client):
    _setup(client)
    pm_id = next(pm["id"] for pm in client.get("/api/v1/payment-methods").json() if pm["name"] == "MyBank")
    cat_id = next(c["id"] for c in client.get("/api/v1/categories").json() if c["type"] == "Salary")
    client.post("/api/v1/transactions", json={
        "date": "2026-01-25", "detail": "Salary", "amount": 2500,
        "payment_method_id": pm_id, "category_id": cat_id, "transaction_direction": "income",
    })
    r = client.get("/api/v1/summary/2026/1")
    assert r.json()["incomes"] == pytest.approx(2500.0)


def test_bank_balance_includes_cc_credit_payoffs(client):
    """CC 'credit'-direction transactions (bank paying off CC) must reduce bank_balance."""
    _setup(client)
    pms = client.get("/api/v1/payment-methods").json()
    cc_id = next(pm["id"] for pm in pms if pm["name"] == "MyCard")
    cat_id = next(c["id"] for c in client.get("/api/v1/categories").json() if c["type"] == "Housing")
    # CC payoff entered in December 2025 — bills in January 2026
    client.post("/api/v1/transactions", json={
        "date": "2025-12-15", "detail": "CC Payoff", "amount": 500,
        "payment_method_id": cc_id, "category_id": cat_id, "transaction_direction": "credit",
    })
    r = client.get("/api/v1/summary/2026/1")
    assert r.status_code == 200
    # Opening balance is 5000; the CC payoff reduces it to 4500
    assert r.json()["bank_balance"] == pytest.approx(4500.0)


def test_summary_month_shows_outcomes_by_method(client):
    _setup(client)
    pm_id = next(pm["id"] for pm in client.get("/api/v1/payment-methods").json() if pm["name"] == "MyBank")
    cat_id = next(c["id"] for c in client.get("/api/v1/categories").json() if c["type"] == "Housing")
    client.post("/api/v1/transactions", json={
        "date": "2026-01-15", "detail": "Rent", "amount": 750,
        "payment_method_id": pm_id, "category_id": cat_id, "transaction_direction": "debit",
    })
    r = client.get("/api/v1/summary/2026/1")
    assert r.status_code == 200
    outcomes = r.json()["outcomes_by_method"]
    assert "MyBank" in outcomes
    assert outcomes["MyBank"] == pytest.approx(750.0)
