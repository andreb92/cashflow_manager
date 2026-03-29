from app.config import Settings


def test_development_mode_defaults_to_false():
    """Production deployments without explicit DEVELOPMENT_MODE must get secure cookie settings."""
    s = Settings(_env_file=None)
    assert s.development_mode is False, (
        "development_mode must default to False so cookies get the Secure flag in production "
        "unless explicitly set to True in a .env file"
    )


def test_short_session_encryption_key_raises():
    """_key_bytes must raise ValueError for keys shorter than 64 hex chars."""
    from app.services.oidc import _key_bytes
    import pytest
    with pytest.raises(ValueError, match="SESSION_ENCRYPTION_KEY"):
        _key_bytes("aabbcc")  # 6 chars — too short


def test_valid_session_encryption_key_accepted():
    from app.services.oidc import _key_bytes
    key = _key_bytes("a" * 64)
    assert len(key) == 32


def test_odd_length_session_key_raises():
    from app.services.oidc import _key_bytes
    import pytest
    with pytest.raises(ValueError):
        _key_bytes("a" * 63)  # 63 hex chars — odd length
