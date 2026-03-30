import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.database import Base
from app.deps import get_db
from app.config import get_settings


@pytest.fixture()
def oidc_client(monkeypatch):
    monkeypatch.setenv("DEVELOPMENT_MODE", "true")
    monkeypatch.setenv("OIDC_ENABLED", "true")
    monkeypatch.setenv("OIDC_ISSUER_URL", "https://example.com/")
    monkeypatch.setenv("OIDC_CLIENT_ID", "client-id")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URI", "http://localhost:8000/api/v1/auth/oidc/callback")
    monkeypatch.setenv("SESSION_ENCRYPTION_KEY", "a" * 64)
    get_settings.cache_clear()

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

    app.dependency_overrides[get_db] = override
    with TestClient(app, raise_server_exceptions=False, follow_redirects=False) as c:
        yield c
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_oidc_login_redirects(oidc_client):
    discovery = {
        "authorization_endpoint": "https://example.com/auth",
        "token_endpoint": "https://example.com/token",
        "end_session_endpoint": "https://example.com/logout",
    }
    with patch("app.services.oidc.discover_endpoints", return_value=discovery):
        resp = oidc_client.get("/api/v1/auth/oidc/login")
    assert resp.status_code in (302, 307)
    assert "https://example.com/auth" in resp.headers["location"]


def test_oidc_logout_reads_id_token_from_cookie(oidc_client):
    """oidc_id_token must be read from the cookie jar, not as a URL query parameter."""
    from unittest.mock import patch
    discovery = {
        "authorization_endpoint": "https://example.com/auth",
        "token_endpoint": "https://example.com/token",
        "end_session_endpoint": "https://example.com/end-session",
    }
    from app.services.oidc import encrypt_cookie
    encrypted = encrypt_cookie("raw-id-token", "a" * 64)
    with patch("app.services.oidc.discover_endpoints", return_value=discovery):
        resp = oidc_client.get(
            "/api/v1/auth/oidc/logout",
            cookies={"oidc_id_token": encrypted},
        )
    # Should redirect to end_session_endpoint with id_token_hint
    assert resp.status_code in (302, 307)
    assert "end-session" in resp.headers["location"]
    assert "raw-id-token" in resp.headers["location"]


def test_aes_encrypt_decrypt_roundtrip():
    from app.services.oidc import encrypt_cookie, decrypt_cookie
    plaintext = "my-id-token"
    enc = encrypt_cookie(plaintext, "a" * 64)
    dec = decrypt_cookie(enc, "a" * 64)
    assert dec == plaintext
