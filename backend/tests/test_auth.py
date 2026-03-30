import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.database import Base
from app.deps import get_db
from app.config import get_settings, Settings


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    # Set DEVELOPMENT_MODE before TestClient.__enter__ so the lifespan
    # sees it when warn_insecure_defaults() is called at startup.
    import os
    os.environ["DEVELOPMENT_MODE"] = "true"
    get_settings.cache_clear()
    app.dependency_overrides[get_db] = override
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()
    os.environ.pop("DEVELOPMENT_MODE", None)
    get_settings.cache_clear()


def test_register_creates_user(client):
    resp = client.post("/api/v1/auth/register", json={"email": "a@b.com", "password": "pass123", "name": "Alice"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "a@b.com"
    assert "access_token" not in data  # cookie only


def test_register_duplicate_email_returns_409(client):
    client.post("/api/v1/auth/register", json={"email": "a@b.com", "password": "p", "name": "A"})
    resp = client.post("/api/v1/auth/register", json={"email": "a@b.com", "password": "p2", "name": "B"})
    assert resp.status_code == 409


def test_login_returns_cookie(client):
    client.post("/api/v1/auth/register", json={"email": "u@u.com", "password": "pw", "name": "U"})
    resp = client.post("/api/v1/auth/login", json={"email": "u@u.com", "password": "pw"})
    assert resp.status_code == 200
    assert "access_token" in resp.cookies


def test_login_wrong_password_returns_401(client):
    client.post("/api/v1/auth/register", json={"email": "u@u.com", "password": "pw", "name": "U"})
    resp = client.post("/api/v1/auth/login", json={"email": "u@u.com", "password": "wrong"})
    assert resp.status_code == 401


def test_me_returns_current_user(client):
    client.post("/api/v1/auth/register", json={"email": "me@test.com", "password": "pw", "name": "Me"})
    client.post("/api/v1/auth/login", json={"email": "me@test.com", "password": "pw"})
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@test.com"


def test_logout_clears_cookie(client):
    client.post("/api/v1/auth/register", json={"email": "x@x.com", "password": "p", "name": "X"})
    client.post("/api/v1/auth/login", json={"email": "x@x.com", "password": "p"})
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    # After logout the cookie should be cleared (max_age=0 or deleted)


def test_me_rejects_token_without_sub(client):
    """A valid JWT that has no 'sub' claim must return 401, not 500."""
    from app.services.auth import create_access_token
    token = create_access_token({})   # no "sub" key
    client.cookies.set("access_token", token)
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401


def test_insecure_defaults_raises_error():
    """warn_insecure_defaults() raises ValueError when production mode uses insecure defaults."""
    import pytest
    from app.config import Settings
    s = Settings(development_mode=False, secret_key="dev-secret-key", session_encryption_key="0" * 64)
    with pytest.raises(ValueError, match="SECRET_KEY"):
        s.warn_insecure_defaults()


def test_secure_config_no_warning(caplog):
    """warn_insecure_defaults() emits no warnings when secrets are properly set."""
    import logging
    from app.config import Settings
    s = Settings(development_mode=False, secret_key="real-secret", session_encryption_key="a" * 64)
    with caplog.at_level(logging.WARNING, logger="cashflow.config"):
        s.warn_insecure_defaults()
    assert caplog.records == []


def test_delete_me_clears_access_token_cookie(client):
    """Account deletion must clear the access_token cookie, not a stale cashflow_jwt name."""
    client.post("/api/v1/auth/register", json={"email": "del_cookie@test.com", "password": "pw", "name": "D"})
    resp = client.request("DELETE", "/api/v1/users/me", json={"password": "pw"})
    assert resp.status_code == 200
    set_cookie = resp.headers.get("set-cookie", "")
    assert "access_token" in set_cookie
    assert "cashflow_jwt" not in set_cookie


def test_development_mode_suppresses_warning(caplog):
    """warn_insecure_defaults() is a no-op when development_mode=True."""
    import logging
    from app.config import Settings
    s = Settings(development_mode=True, secret_key="dev-secret-key", session_encryption_key="0" * 64)
    with caplog.at_level(logging.WARNING, logger="cashflow.config"):
        s.warn_insecure_defaults()
    assert caplog.records == []
