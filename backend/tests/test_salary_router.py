from tests.conftest import *  # noqa: F401,F403


def _make_user_and_login(client):
    client.post("/api/v1/auth/register", json={"email": "u@x.com", "password": "pass123", "name": "U"})
    client.post("/api/v1/auth/login", json={"email": "u@x.com", "password": "pass123"})


def test_create_salary_with_salary_months_13(client):
    _make_user_and_login(client)
    resp = client.post("/api/v1/salary", json={
        "valid_from": "2026-01-01",
        "ral": 36000,
        "employer_contrib_rate": 0.02,
        "voluntary_contrib_rate": 0.01,
        "regional_tax_rate": 0.0173,
        "municipal_tax_rate": 0.001,
        "meal_vouchers_annual": 0,
        "welfare_annual": 0,
        "salary_months": 13,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["salary_months"] == 13


def test_calculate_endpoint_returns_english_field_names(client):
    _make_user_and_login(client)
    resp = client.get("/api/v1/salary/calculate", params={
        "as_of": "2026-01",
        "ral": 36000,
        "employer_contrib_rate": 0.02,
        "voluntary_contrib_rate": 0.01,
        "regional_tax_rate": 0.0173,
        "municipal_tax_rate": 0.001,
        "salary_months": 12,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "net_monthly" in data
    assert "gross_annual" in data
    assert "netto_mensile" not in data  # old Italian name gone


def test_calculate_salary_months_affects_net_monthly(client):
    _make_user_and_login(client)
    base = {"as_of": "2026-01", "ral": 36000, "employer_contrib_rate": 0.02,
            "voluntary_contrib_rate": 0.01, "regional_tax_rate": 0.0173,
            "municipal_tax_rate": 0.001}
    r12 = client.get("/api/v1/salary/calculate", params={**base, "salary_months": 12}).json()
    r13 = client.get("/api/v1/salary/calculate", params={**base, "salary_months": 13}).json()
    assert r12["net_monthly"] > r13["net_monthly"]
    assert abs(r12["net_monthly"] / r13["net_monthly"] - 13 / 12) < 0.01


def test_preview_salary_returns_422_when_no_tax_config(client):
    _make_user_and_login(client)
    # Tax config is seeded starting 2026-01-01; use a date before that
    r = client.get("/api/v1/salary/calculate", params={
        "as_of": "1990-01",
        "ral": 36000,
        "employer_contrib_rate": 0.02,
        "voluntary_contrib_rate": 0.01,
        "regional_tax_rate": 0.0173,
        "municipal_tax_rate": 0.001,
        "salary_months": 12,
    })
    assert r.status_code == 422


def test_update_salary(client):
    _make_user_and_login(client)
    salary_id = client.post("/api/v1/salary", json={
        "valid_from": "2026-01-01",
        "ral": 36000,
        "employer_contrib_rate": 0.02,
        "voluntary_contrib_rate": 0.01,
        "regional_tax_rate": 0.0173,
        "municipal_tax_rate": 0.001,
        "salary_months": 12,
    }).json()["id"]
    r = client.put(f"/api/v1/salary/{salary_id}", json={
        "valid_from": "2026-01-01",
        "ral": 42000,
        "employer_contrib_rate": 0.02,
        "voluntary_contrib_rate": 0.01,
        "regional_tax_rate": 0.0173,
        "municipal_tax_rate": 0.001,
        "salary_months": 12,
    })
    assert r.status_code == 200
    assert r.json()["ral"] == 42000


def test_update_salary_not_found(client):
    _make_user_and_login(client)
    r = client.put("/api/v1/salary/nonexistent-id", json={
        "valid_from": "2026-01-01",
        "ral": 36000,
        "employer_contrib_rate": 0.02,
        "voluntary_contrib_rate": 0.01,
        "regional_tax_rate": 0.0173,
        "municipal_tax_rate": 0.001,
        "salary_months": 12,
    })
    assert r.status_code == 404


def test_delete_salary_not_earliest(client):
    _make_user_and_login(client)
    # Create the earliest salary entry
    client.post("/api/v1/salary", json={
        "valid_from": "2025-01-01",
        "ral": 30000,
        "employer_contrib_rate": 0.02,
        "voluntary_contrib_rate": 0.01,
        "regional_tax_rate": 0.0173,
        "municipal_tax_rate": 0.001,
        "salary_months": 12,
    })
    # Create a second (later) salary entry
    second_id = client.post("/api/v1/salary", json={
        "valid_from": "2026-01-01",
        "ral": 36000,
        "employer_contrib_rate": 0.02,
        "voluntary_contrib_rate": 0.01,
        "regional_tax_rate": 0.0173,
        "municipal_tax_rate": 0.001,
        "salary_months": 12,
    }).json()["id"]
    # Deleting the non-earliest should succeed
    r = client.delete(f"/api/v1/salary/{second_id}")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_delete_salary_earliest_returns_400(client):
    _make_user_and_login(client)
    # Create two salary entries
    earliest_id = client.post("/api/v1/salary", json={
        "valid_from": "2025-01-01",
        "ral": 30000,
        "employer_contrib_rate": 0.02,
        "voluntary_contrib_rate": 0.01,
        "regional_tax_rate": 0.0173,
        "municipal_tax_rate": 0.001,
        "salary_months": 12,
    }).json()["id"]
    client.post("/api/v1/salary", json={
        "valid_from": "2026-01-01",
        "ral": 36000,
        "employer_contrib_rate": 0.02,
        "voluntary_contrib_rate": 0.01,
        "regional_tax_rate": 0.0173,
        "municipal_tax_rate": 0.001,
        "salary_months": 12,
    })
    # Deleting the earliest should be rejected
    r = client.delete(f"/api/v1/salary/{earliest_id}")
    assert r.status_code == 400


def test_delete_salary_not_found(client):
    _make_user_and_login(client)
    r = client.delete("/api/v1/salary/nonexistent-id")
    assert r.status_code == 404


def test_create_salary_months_zero_returns_422(client):
    _make_user_and_login(client)
    resp = client.post("/api/v1/salary", json={
        "valid_from": "2026-01-01", "ral": 36000,
        "employer_contrib_rate": 0.0, "voluntary_contrib_rate": 0.0,
        "regional_tax_rate": 0.0, "municipal_tax_rate": 0.0,
        "salary_months": 0,
    })
    assert resp.status_code == 422


def test_calculate_salary_months_zero_returns_422(client):
    _make_user_and_login(client)
    resp = client.get("/api/v1/salary/calculate", params={
        "as_of": "2026-01", "ral": 36000,
        "employer_contrib_rate": 0.0, "voluntary_contrib_rate": 0.0,
        "regional_tax_rate": 0.0, "municipal_tax_rate": 0.0,
        "salary_months": 0,
    })
    assert resp.status_code == 422
