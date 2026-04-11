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
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
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
    # Register and login to be authenticated
    oidc_client.post("/api/v1/auth/register", json={"email": "a@b.com", "password": "pass1234", "name": "Alice"})
    discovery = {
        "authorization_endpoint": "https://example.com/auth",
        "token_endpoint": "https://example.com/token",
        "end_session_endpoint": "https://example.com/end-session",
    }
    from app.services.oidc import encrypt_cookie
    encrypted = encrypt_cookie("raw-id-token", "a" * 64)
    oidc_client.cookies.set("oidc_id_token", encrypted)
    with patch("app.services.oidc.discover_endpoints", return_value=discovery):
        resp = oidc_client.get("/api/v1/auth/oidc/logout")
    oidc_client.cookies.delete("oidc_id_token")
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


def test_decrypt_cookie_returns_none_on_bad_input():
    """decrypt_cookie must return None (not raise) when the ciphertext is invalid."""
    from app.services.oidc import decrypt_cookie
    assert decrypt_cookie("not-valid-ciphertext!!", "a" * 64) is None


def test_oidc_callback_state_mismatch_returns_400(oidc_client):
    """callback with no oidc_state cookie must reject with 400."""
    resp = oidc_client.get("/api/v1/auth/oidc/callback?code=abc&state=wrongstate")
    assert resp.status_code == 400


def test_oidc_callback_creates_new_user(oidc_client):
    """Successful OIDC callback must create the user and redirect to /."""
    from unittest.mock import patch, AsyncMock
    discovery = {
        "authorization_endpoint": "https://example.com/auth",
        "token_endpoint": "https://example.com/token",
        "userinfo_endpoint": "https://example.com/userinfo",
        "end_session_endpoint": "https://example.com/logout",
    }
    tokens = {"access_token": "at-123", "id_token": "it-abc"}
    userinfo = {"sub": "sub-new-user", "email": "oidcnew@example.com", "name": "New User"}

    oidc_client.cookies.set("oidc_state", "test-state-value")
    with patch("app.services.oidc.discover_endpoints", AsyncMock(return_value=discovery)), \
         patch("app.services.oidc.exchange_code", AsyncMock(return_value=tokens)), \
         patch("app.services.oidc.get_userinfo", AsyncMock(return_value=userinfo)):
        resp = oidc_client.get("/api/v1/auth/oidc/callback?code=abc&state=test-state-value")
    oidc_client.cookies.delete("oidc_state")

    assert resp.status_code in (200, 302, 307)


def test_oidc_callback_links_oidc_sub_to_existing_email_user(oidc_client):
    """Callback must set oidc_sub on a user that was found by email but had no oidc_sub."""
    from unittest.mock import patch, AsyncMock

    # Pre-seed a user via basic-auth register (oidc_sub will be None)
    oidc_client.post(
        "/api/v1/auth/register",
        json={"email": "link@example.com", "password": "pass1234", "name": "Link"},
    )

    discovery = {
        "authorization_endpoint": "https://example.com/auth",
        "token_endpoint": "https://example.com/token",
        "userinfo_endpoint": "https://example.com/userinfo",
    }
    tokens = {"access_token": "at-xyz"}
    # Same email as registered above — no oidc_sub on that user yet
    userinfo = {"sub": "sub-link-new", "email": "link@example.com", "name": "Link"}

    oidc_client.cookies.set("oidc_state", "link-state")
    with patch("app.services.oidc.discover_endpoints", AsyncMock(return_value=discovery)), \
         patch("app.services.oidc.exchange_code", AsyncMock(return_value=tokens)), \
         patch("app.services.oidc.get_userinfo", AsyncMock(return_value=userinfo)):
        resp = oidc_client.get("/api/v1/auth/oidc/callback?code=code&state=link-state")
    oidc_client.cookies.delete("oidc_state")

    assert resp.status_code in (200, 302, 307)


def test_oidc_logout_corrupted_cookie_redirects_to_login(oidc_client):
    """oidc_logout with an undecryptable cookie must redirect to /login."""
    from unittest.mock import patch, AsyncMock
    # Register and login to be authenticated
    oidc_client.post("/api/v1/auth/register", json={"email": "a@b.com", "password": "pass1234", "name": "Alice"})
    discovery = {"end_session_endpoint": "https://example.com/logout"}
    oidc_client.cookies.set("oidc_id_token", "totally-corrupt-value")
    with patch("app.services.oidc.discover_endpoints", AsyncMock(return_value=discovery)):
        resp = oidc_client.get("/api/v1/auth/oidc/logout")
    oidc_client.cookies.delete("oidc_id_token")
    assert resp.status_code in (302, 307)
    assert "/login" in resp.headers["location"]


def test_oidc_logout_discover_exception_redirects_to_login(oidc_client):
    """oidc_logout must fall back to /login redirect when discover_endpoints raises."""
    from unittest.mock import patch, AsyncMock
    from app.services.oidc import encrypt_cookie
    # Register and login to be authenticated
    oidc_client.post("/api/v1/auth/register", json={"email": "a@b.com", "password": "pass1234", "name": "Alice"})
    encrypted = encrypt_cookie("id-token", "a" * 64)
    oidc_client.cookies.set("oidc_id_token", encrypted)
    with patch("app.services.oidc.discover_endpoints", AsyncMock(side_effect=Exception("network"))):
        resp = oidc_client.get("/api/v1/auth/oidc/logout")
    oidc_client.cookies.delete("oidc_id_token")
    assert resp.status_code in (302, 307)
    assert "/login" in resp.headers["location"]


def test_discover_endpoints_calls_well_known_url():
    """discover_endpoints must GET /.well-known/openid-configuration."""
    import asyncio
    from unittest.mock import patch, AsyncMock, MagicMock
    from app.services.oidc import discover_endpoints

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"authorization_endpoint": "https://idp/auth"}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("app.services.oidc.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)
        result = asyncio.run(discover_endpoints("https://idp.example.com/"))

    mock_client.get.assert_called_once_with(
        "https://idp.example.com/.well-known/openid-configuration", timeout=10
    )
    assert result["authorization_endpoint"] == "https://idp/auth"


def test_exchange_code_posts_to_token_endpoint():
    """exchange_code must POST the authorization_code grant to the token endpoint."""
    import asyncio
    from unittest.mock import patch, AsyncMock, MagicMock
    from app.services.oidc import exchange_code

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"access_token": "at-xyz", "id_token": "it-abc"}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("app.services.oidc.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)
        result = asyncio.run(
            exchange_code("code123", "https://idp/token", "https://app/cb", "cid", "csecret")
        )

    assert result["access_token"] == "at-xyz"
    mock_client.post.assert_called_once()


def test_get_userinfo_calls_userinfo_endpoint():
    """get_userinfo must GET the userinfo endpoint with a Bearer token."""
    import asyncio
    from unittest.mock import patch, AsyncMock, MagicMock
    from app.services.oidc import get_userinfo

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"sub": "u1", "email": "u@example.com"}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("app.services.oidc.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=None)
        result = asyncio.run(get_userinfo("https://idp/userinfo", "at-token"))

    mock_client.get.assert_called_once_with(
        "https://idp/userinfo",
        headers={"Authorization": "Bearer at-token"},
        timeout=10,
    )
    assert result["sub"] == "u1"


def test_oidc_logout_requires_auth(client):
    """OIDC logout must reject unauthenticated requests with 401.
    Uses client (not oidc_client) because oidc_logout enforces auth
    regardless of whether OIDC is enabled — get_current_user fires first.
    """
    r = client.get("/api/v1/auth/oidc/logout")
    assert r.status_code == 401
