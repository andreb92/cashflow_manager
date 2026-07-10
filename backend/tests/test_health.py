def test_health_ok(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_health_requires_no_auth(client):
    # No login/cookie set, must still succeed
    r = client.get("/api/v1/health")
    assert r.status_code == 200
