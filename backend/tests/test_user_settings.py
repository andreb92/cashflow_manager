from tests.test_onboarding import WIZARD_PAYLOAD

def _setup(client):
    client.post("/api/v1/auth/register", json={
        "email": "alice@example.com", "password": "Password1!", "name": "Alice"
    })
    client.post("/api/v1/onboarding", json=WIZARD_PAYLOAD)

def test_get_user_settings_returns_all_keys(client):
    _setup(client)
    r = client.get("/api/v1/user-settings")
    assert r.status_code == 200
    keys = {item["key"] for item in r.json()}
    assert "tracking_start_date" in keys
    assert "onboarding_complete" in keys

def test_update_user_setting(client):
    _setup(client)
    client.put("/api/v1/user-settings", json=[{"key": "theme", "value": "dark"}])
    r = client.get("/api/v1/user-settings")
    keys = {item["key"]: item["value"] for item in r.json()}
    assert keys.get("theme") == "dark"

def test_update_user_setting_invalid_key_returns_422(client):
    """Backend must reject unknown setting keys with 422."""
    _setup(client)
    r = client.put("/api/v1/user-settings", json=[{"key": "injected_key", "value": "x"}])
    assert r.status_code == 422

def test_users_me_returns_profile(client):
    client.post("/api/v1/auth/register", json={
        "email": "alice@example.com", "password": "Password1!", "name": "Alice"
    })
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "alice@example.com"

def test_delete_own_account(client, db):
    client.post("/api/v1/auth/register", json={
        "email": "alice@example.com", "password": "Password1!", "name": "Alice"
    })
    r = client.request("DELETE", "/api/v1/users/me", json={"password": "Password1!"})
    assert r.status_code == 200
    # Should now be unauthenticated
    assert client.get("/api/v1/auth/me").status_code == 401
