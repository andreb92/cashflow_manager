import time
from app.services.auth import hash_password, verify_password, create_access_token, decode_access_token


def test_hash_and_verify():
    hashed = hash_password("secret")
    assert verify_password("secret", hashed)
    assert not verify_password("wrong", hashed)


def test_create_and_decode_token():
    token = create_access_token({"sub": "user-1"})
    payload = decode_access_token(token)
    assert payload["sub"] == "user-1"


def test_invalid_token_returns_none():
    assert decode_access_token("not.a.token") is None


def test_expired_token_returns_none():
    token = create_access_token({"sub": "x"}, expires_delta_seconds=-1)
    time.sleep(0.05)
    assert decode_access_token(token) is None
