import pytest
from tests.test_onboarding import WIZARD_PAYLOAD

def _setup(client):
    client.post("/api/v1/auth/register", json={
        "email": "alice@example.com", "password": "Password1!", "name": "Alice"
    })
    client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)
    pm_id = next(pm["id"] for pm in client.get("/api/v1/payment-methods").json() if pm["name"] == "MyBank")
    cat_id = next(c["id"] for c in client.get("/api/v1/categories").json() if c["type"] == "Mobility")
    # Create a recurring expense in 2026 to use as base
    client.post("/api/v1/transactions", json={
        "date": "2026-01-05", "detail": "Car loan", "amount": 350,
        "payment_method_id": pm_id, "category_id": cat_id,
        "transaction_direction": "debit", "recurrence_months": 12,
    })
    return pm_id, cat_id

def test_create_forecast(client):
    _setup(client)
    r = client.post("/api/v1/forecasts", json={"name": "3-year plan", "base_year": 2026, "projection_years": 3})
    assert r.status_code == 200
    assert r.json()["name"] == "3-year plan"

def test_forecast_auto_generates_lines_from_recurring(client):
    _setup(client)
    fc_id = client.post("/api/v1/forecasts", json={"name": "Plan", "base_year": 2026, "projection_years": 3}).json()["id"]
    r = client.get(f"/api/v1/forecasts/{fc_id}")
    assert r.status_code == 200
    lines = r.json()["lines"]
    assert any(l["detail"] == "Car loan" for l in lines)

def test_forecast_projection_covers_correct_years(client):
    _setup(client)
    fc_id = client.post("/api/v1/forecasts", json={"name": "Plan", "base_year": 2026, "projection_years": 2}).json()["id"]
    r = client.get(f"/api/v1/forecasts/{fc_id}/projection")
    assert r.status_code == 200
    data = r.json()
    assert data["period"]["from"] == "2027-01"
    assert data["period"]["to"] == "2028-12"

def test_forecast_projection_uses_base_amount(client):
    _setup(client)
    fc_id = client.post("/api/v1/forecasts", json={"name": "Plan", "base_year": 2026, "projection_years": 1}).json()["id"]
    proj = client.get(f"/api/v1/forecasts/{fc_id}/projection").json()
    car_line = next((l for l in proj["lines"] if l["detail"] == "Car loan"), None)
    assert car_line is not None
    assert all(m["effective_amount"] == pytest.approx(350.0) for m in car_line["months"])

def test_adjustment_changes_amount_from_valid_from(client):
    _setup(client)
    fc_id = client.post("/api/v1/forecasts", json={"name": "Plan", "base_year": 2026, "projection_years": 2}).json()["id"]
    line_id = next(l["id"] for l in client.get(f"/api/v1/forecasts/{fc_id}").json()["lines"] if l["detail"] == "Car loan")
    client.post(f"/api/v1/forecasts/{fc_id}/lines/{line_id}/adjustments", json={
        "valid_from": "2028-03-01", "new_amount": 450.0
    })
    proj = client.get(f"/api/v1/forecasts/{fc_id}/projection").json()
    car_line = next(l for l in proj["lines"] if l["detail"] == "Car loan")
    months = {m["month"]: m["effective_amount"] for m in car_line["months"]}
    assert months["2028-02"] == pytest.approx(350.0)
    assert months["2028-03"] == pytest.approx(450.0)
    assert months["2028-12"] == pytest.approx(450.0)

def test_reduce_projection_years_deletes_out_of_range_adjustments(client):
    _setup(client)
    fc_id = client.post("/api/v1/forecasts", json={"name": "Plan", "base_year": 2026, "projection_years": 3}).json()["id"]
    line_id = next(l["id"] for l in client.get(f"/api/v1/forecasts/{fc_id}").json()["lines"] if l["detail"] == "Car loan")
    client.post(f"/api/v1/forecasts/{fc_id}/lines/{line_id}/adjustments", json={
        "valid_from": "2029-06-01", "new_amount": 500.0
    })
    client.put(f"/api/v1/forecasts/{fc_id}", json={"name": "Plan", "projection_years": 1})
    fc = client.get(f"/api/v1/forecasts/{fc_id}").json()
    for line in fc["lines"]:
        assert all(a["valid_from"] <= "2027-12-01" for a in line["adjustments"])

def test_delete_forecast(client):
    _setup(client)
    fc_id = client.post("/api/v1/forecasts", json={"name": "Plan", "base_year": 2026, "projection_years": 1}).json()["id"]
    assert client.delete(f"/api/v1/forecasts/{fc_id}").status_code == 200
    assert client.get(f"/api/v1/forecasts/{fc_id}").status_code == 404


def test_list_forecasts_returns_list(client):
    _setup(client)
    r = client.get("/api/v1/forecasts")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_list_forecasts_includes_created_forecast(client):
    _setup(client)
    client.post("/api/v1/forecasts", json={"name": "My Plan", "base_year": 2026, "projection_years": 1})
    r = client.get("/api/v1/forecasts")
    assert any(fc["name"] == "My Plan" for fc in r.json())


def test_update_forecast_not_found(client):
    _setup(client)
    r = client.put("/api/v1/forecasts/nonexistent-id", json={"name": "New Name"})
    assert r.status_code == 404


def test_delete_forecast_not_found(client):
    _setup(client)
    r = client.delete("/api/v1/forecasts/nonexistent-id")
    assert r.status_code == 404


def test_get_projection_not_found(client):
    _setup(client)
    r = client.get("/api/v1/forecasts/nonexistent-id/projection")
    assert r.status_code == 404


def test_add_line_to_forecast(client):
    _setup(client)
    fc_id = client.post("/api/v1/forecasts", json={"name": "Plan", "base_year": 2026, "projection_years": 1}).json()["id"]
    r = client.post(f"/api/v1/forecasts/{fc_id}/lines", json={
        "detail": "Extra expense", "base_amount": 100.0, "billing_day": 15,
    })
    assert r.status_code == 200
    assert r.json()["detail"] == "Extra expense"
    assert r.json()["base_amount"] == 100.0


def test_add_line_to_nonexistent_forecast(client):
    _setup(client)
    r = client.post("/api/v1/forecasts/nonexistent-id/lines", json={
        "detail": "Ghost", "base_amount": 50.0,
    })
    assert r.status_code == 404


def test_update_line(client):
    _setup(client)
    fc_id = client.post("/api/v1/forecasts", json={"name": "Plan", "base_year": 2026, "projection_years": 1}).json()["id"]
    line_id = client.post(f"/api/v1/forecasts/{fc_id}/lines", json={
        "detail": "Old name", "base_amount": 200.0,
    }).json()["id"]
    r = client.put(f"/api/v1/forecasts/{fc_id}/lines/{line_id}", json={
        "detail": "New name", "base_amount": 300.0,
    })
    assert r.status_code == 200
    assert r.json()["detail"] == "New name"
    assert r.json()["base_amount"] == 300.0


def test_update_line_not_found(client):
    _setup(client)
    fc_id = client.post("/api/v1/forecasts", json={"name": "Plan", "base_year": 2026, "projection_years": 1}).json()["id"]
    r = client.put(f"/api/v1/forecasts/{fc_id}/lines/nonexistent-line-id", json={
        "detail": "Ghost", "base_amount": 50.0,
    })
    assert r.status_code == 404


def test_delete_line(client):
    _setup(client)
    fc_id = client.post("/api/v1/forecasts", json={"name": "Plan", "base_year": 2026, "projection_years": 1}).json()["id"]
    line_id = client.post(f"/api/v1/forecasts/{fc_id}/lines", json={
        "detail": "Temp line", "base_amount": 75.0,
    }).json()["id"]
    r = client.delete(f"/api/v1/forecasts/{fc_id}/lines/{line_id}")
    assert r.status_code == 200
    fc = client.get(f"/api/v1/forecasts/{fc_id}").json()
    assert not any(l["id"] == line_id for l in fc["lines"])


def test_delete_line_not_found(client):
    _setup(client)
    fc_id = client.post("/api/v1/forecasts", json={"name": "Plan", "base_year": 2026, "projection_years": 1}).json()["id"]
    r = client.delete(f"/api/v1/forecasts/{fc_id}/lines/nonexistent-line-id")
    assert r.status_code == 404


def test_add_adjustment_forecast_not_found(client):
    _setup(client)
    r = client.post("/api/v1/forecasts/nonexistent-id/lines/some-line/adjustments", json={
        "valid_from": "2027-01-01", "new_amount": 500.0,
    })
    assert r.status_code == 404


def test_add_adjustment_line_not_found(client):
    _setup(client)
    fc_id = client.post("/api/v1/forecasts", json={"name": "Plan", "base_year": 2026, "projection_years": 2}).json()["id"]
    r = client.post(f"/api/v1/forecasts/{fc_id}/lines/nonexistent-line-id/adjustments", json={
        "valid_from": "2027-01-01", "new_amount": 500.0,
    })
    assert r.status_code == 404


def test_add_adjustment_valid_from_out_of_range(client):
    _setup(client)
    fc_id = client.post("/api/v1/forecasts", json={"name": "Plan", "base_year": 2026, "projection_years": 1}).json()["id"]
    line_id = next(l["id"] for l in client.get(f"/api/v1/forecasts/{fc_id}").json()["lines"] if l["detail"] == "Car loan")
    # valid_from is before the projection start (2027-01-01)
    r = client.post(f"/api/v1/forecasts/{fc_id}/lines/{line_id}/adjustments", json={
        "valid_from": "2026-06-01", "new_amount": 999.0,
    })
    assert r.status_code == 422


def test_update_adjustment(client):
    _setup(client)
    fc_id = client.post("/api/v1/forecasts", json={"name": "Plan", "base_year": 2026, "projection_years": 2}).json()["id"]
    line_id = next(l["id"] for l in client.get(f"/api/v1/forecasts/{fc_id}").json()["lines"] if l["detail"] == "Car loan")
    adj_id = client.post(f"/api/v1/forecasts/{fc_id}/lines/{line_id}/adjustments", json={
        "valid_from": "2027-06-01", "new_amount": 400.0,
    }).json()["id"]
    r = client.put(f"/api/v1/forecasts/{fc_id}/lines/{line_id}/adjustments/{adj_id}", json={
        "valid_from": "2027-09-01", "new_amount": 550.0,
    })
    assert r.status_code == 200
    assert r.json()["new_amount"] == 550.0
    assert r.json()["valid_from"] == "2027-09-01"


def test_update_adjustment_not_found(client):
    _setup(client)
    fc_id = client.post("/api/v1/forecasts", json={"name": "Plan", "base_year": 2026, "projection_years": 2}).json()["id"]
    line_id = next(l["id"] for l in client.get(f"/api/v1/forecasts/{fc_id}").json()["lines"] if l["detail"] == "Car loan")
    r = client.put(f"/api/v1/forecasts/{fc_id}/lines/{line_id}/adjustments/nonexistent-adj-id", json={
        "valid_from": "2027-06-01", "new_amount": 400.0,
    })
    assert r.status_code == 404


def test_delete_adjustment(client):
    _setup(client)
    fc_id = client.post("/api/v1/forecasts", json={"name": "Plan", "base_year": 2026, "projection_years": 2}).json()["id"]
    line_id = next(l["id"] for l in client.get(f"/api/v1/forecasts/{fc_id}").json()["lines"] if l["detail"] == "Car loan")
    adj_id = client.post(f"/api/v1/forecasts/{fc_id}/lines/{line_id}/adjustments", json={
        "valid_from": "2027-03-01", "new_amount": 420.0,
    }).json()["id"]
    r = client.delete(f"/api/v1/forecasts/{fc_id}/lines/{line_id}/adjustments/{adj_id}")
    assert r.status_code == 200
    fc = client.get(f"/api/v1/forecasts/{fc_id}").json()
    line = next(l for l in fc["lines"] if l["id"] == line_id)
    assert not any(a["id"] == adj_id for a in line["adjustments"])


def test_delete_adjustment_not_found(client):
    _setup(client)
    fc_id = client.post("/api/v1/forecasts", json={"name": "Plan", "base_year": 2026, "projection_years": 2}).json()["id"]
    line_id = next(l["id"] for l in client.get(f"/api/v1/forecasts/{fc_id}").json()["lines"] if l["detail"] == "Car loan")
    r = client.delete(f"/api/v1/forecasts/{fc_id}/lines/{line_id}/adjustments/nonexistent-adj-id")
    assert r.status_code == 404


def test_forecast_detail_bulk_loads_adjustments(client):
    """GET /{fc_id} must return all adjustments regardless of how many lines exist."""
    from tests.test_onboarding import WIZARD_PAYLOAD

    client.post("/api/v1/auth/register", json={
        "email": "fc_bulk@test.com", "password": "Password1!", "name": "FcBulk"
    })
    client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)

    fc = client.post("/api/v1/forecasts", json={
        "name": "BulkTest", "base_year": 2025, "projection_years": 1
    }).json()
    fc_id = fc["id"]

    # Add 3 manual lines
    line_ids = []
    for i in range(3):
        line = client.post(f"/api/v1/forecasts/{fc_id}/lines", json={
            "detail": f"Line {i}", "base_amount": 100.0
        }).json()
        line_ids.append(line["id"])

    # Add one adjustment per line
    for line_id in line_ids:
        client.post(f"/api/v1/forecasts/{fc_id}/lines/{line_id}/adjustments", json={
            "valid_from": "2026-06-01", "new_amount": 200.0
        })

    detail = client.get(f"/api/v1/forecasts/{fc_id}").json()
    # Every line must have its adjustment
    for line in detail["lines"]:
        if line["id"] in line_ids:
            assert len(line["adjustments"]) == 1, \
                f"Line {line['id']} missing adjustment"


# ---------------------------------------------------------------------------
# H-4: project_forecast must respect user_id — another user cannot trigger it
# ---------------------------------------------------------------------------
def test_project_forecast_wrong_user_returns_404(client):
    """Projection endpoint must 404 when the forecast belongs to a different user."""
    from tests.test_onboarding import WIZARD_PAYLOAD

    # Alice creates a forecast
    client.post("/api/v1/auth/register", json={
        "email": "alice_h4@test.com", "password": "Password1!", "name": "Alice"
    })
    client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)
    fc_id = client.post("/api/v1/forecasts", json={
        "name": "Alice plan", "base_year": 2026, "projection_years": 1
    }).json()["id"]

    # Bob registers and logs in (cookie is now Bob's session)
    client.post("/api/v1/auth/register", json={
        "email": "bob_h4@test.com", "password": "Password1!", "name": "Bob"
    })
    client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)

    # Bob tries to access Alice's projection — must get 404
    r = client.get(f"/api/v1/forecasts/{fc_id}/projection")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# H-5: updating a forecast name to empty string must be accepted
# ---------------------------------------------------------------------------
def test_update_forecast_name_to_empty_string(client):
    """Setting name='' is a valid update and must not be silently skipped."""
    _setup(client)
    fc_id = client.post("/api/v1/forecasts", json={
        "name": "Original Name", "base_year": 2026, "projection_years": 1
    }).json()["id"]

    r = client.put(f"/api/v1/forecasts/{fc_id}", json={"name": ""})
    assert r.status_code == 200
    assert r.json()["name"] == ""


# ---------------------------------------------------------------------------
# H-6: add_line response must contain the expected dict fields
# ---------------------------------------------------------------------------
def test_add_line_response_has_expected_fields(client):
    """add_line must return a dict with the same fields as _forecast_detail line entries."""
    _setup(client)
    fc_id = client.post("/api/v1/forecasts", json={
        "name": "Plan", "base_year": 2026, "projection_years": 1
    }).json()["id"]

    r = client.post(f"/api/v1/forecasts/{fc_id}/lines", json={
        "detail": "New line", "base_amount": 123.45, "billing_day": 10,
    })
    assert r.status_code == 200
    body = r.json()
    for field in ("id", "detail", "base_amount", "billing_day", "category_id",
                  "payment_method_id", "notes", "adjustments"):
        assert field in body, f"Missing field: {field}"
    assert body["detail"] == "New line"
    assert body["base_amount"] == pytest.approx(123.45)
    assert body["billing_day"] == 10
    assert body["adjustments"] == []


# --- Group 3: percentage adjustments ---

def _make_forecast_with_line(client, base_amount: float, projection_years: int = 1) -> tuple[str, str]:
    """Create a forecast with a single manual line; return (fc_id, line_id)."""
    _setup(client)
    fc_id = client.post("/api/v1/forecasts", json={
        "name": "PctTest", "base_year": 2026, "projection_years": projection_years,
    }).json()["id"]
    line_id = client.post(f"/api/v1/forecasts/{fc_id}/lines", json={
        "detail": "PctLine", "base_amount": base_amount,
    }).json()["id"]
    return fc_id, line_id


def test_percentage_adjustment_positive(client):
    """A 10% adjustment on base_amount=1000 must yield effective_amount=1100.0 in the projection."""
    fc_id, line_id = _make_forecast_with_line(client, base_amount=1000.0)
    client.post(f"/api/v1/forecasts/{fc_id}/lines/{line_id}/adjustments", json={
        "valid_from": "2027-01-01", "new_amount": 10.0, "adjustment_type": "percentage",
    })
    proj = client.get(f"/api/v1/forecasts/{fc_id}/projection").json()
    pct_line = next(l for l in proj["lines"] if l["detail"] == "PctLine")
    # All months from 2027-01 onward should show 1100
    for m in pct_line["months"]:
        assert m["effective_amount"] == pytest.approx(1100.0), (
            f"Expected 1100.0 for month {m['month']}, got {m['effective_amount']}"
        )


def test_percentage_adjustment_zero_percent(client):
    """A 0% adjustment on base_amount=1000 must leave effective_amount unchanged at 1000.0."""
    fc_id, line_id = _make_forecast_with_line(client, base_amount=1000.0)
    client.post(f"/api/v1/forecasts/{fc_id}/lines/{line_id}/adjustments", json={
        "valid_from": "2027-01-01", "new_amount": 0.0, "adjustment_type": "percentage",
    })
    proj = client.get(f"/api/v1/forecasts/{fc_id}/projection").json()
    pct_line = next(l for l in proj["lines"] if l["detail"] == "PctLine")
    for m in pct_line["months"]:
        assert m["effective_amount"] == pytest.approx(1000.0), (
            f"Expected 1000.0 for month {m['month']}, got {m['effective_amount']}"
        )


def test_percentage_adjustment_negative_percent(client):
    """A -20% adjustment on base_amount=1000 must yield effective_amount=800.0."""
    fc_id, line_id = _make_forecast_with_line(client, base_amount=1000.0)
    client.post(f"/api/v1/forecasts/{fc_id}/lines/{line_id}/adjustments", json={
        "valid_from": "2027-01-01", "new_amount": -20.0, "adjustment_type": "percentage",
    })
    proj = client.get(f"/api/v1/forecasts/{fc_id}/projection").json()
    pct_line = next(l for l in proj["lines"] if l["detail"] == "PctLine")
    for m in pct_line["months"]:
        assert m["effective_amount"] == pytest.approx(800.0), (
            f"Expected 800.0 for month {m['month']}, got {m['effective_amount']}"
        )
