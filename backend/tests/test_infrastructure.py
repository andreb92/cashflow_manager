"""Tests for database.py and deps.py infrastructure that is always overridden in API tests."""
import os
import tempfile
import pytest


def test_get_engine_creates_sqlite_engine(tmp_path):
    """get_engine() must create an engine pointing at settings.db_path."""
    from app.database import get_engine
    from app.config import get_settings

    db_file = str(tmp_path / "test.db")
    os.environ["DB_PATH"] = db_file
    os.environ["DEVELOPMENT_MODE"] = "true"
    get_settings.cache_clear()
    get_engine.cache_clear()
    try:
        engine = get_engine()
        assert engine is not None
        assert "sqlite" in str(engine.url)
    finally:
        get_engine.cache_clear()
        os.environ.pop("DB_PATH", None)
        os.environ.pop("DEVELOPMENT_MODE", None)
        get_settings.cache_clear()


def test_get_session_factory_returns_callable(tmp_path):
    """get_session_factory() must return a sessionmaker bound to get_engine()."""
    from app.database import get_engine, get_session_factory, Base
    from app.config import get_settings

    db_file = str(tmp_path / "test2.db")
    os.environ["DB_PATH"] = db_file
    os.environ["DEVELOPMENT_MODE"] = "true"
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    try:
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        factory = get_session_factory()
        session = factory()
        session.close()
        Base.metadata.drop_all(bind=engine)
    finally:
        get_engine.cache_clear()
        get_session_factory.cache_clear()
        os.environ.pop("DB_PATH", None)
        os.environ.pop("DEVELOPMENT_MODE", None)
        get_settings.cache_clear()


def test_get_db_yields_and_closes(tmp_path):
    """get_db() must yield a session and close it on exit."""
    from app.database import get_engine, get_session_factory, Base
    from app.deps import get_db
    from app.config import get_settings

    db_file = str(tmp_path / "test3.db")
    os.environ["DB_PATH"] = db_file
    os.environ["DEVELOPMENT_MODE"] = "true"
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    try:
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        gen = get_db()
        session = next(gen)
        assert session is not None
        try:
            gen.close()
        except StopIteration:
            pass
        Base.metadata.drop_all(bind=engine)
    finally:
        get_engine.cache_clear()
        get_session_factory.cache_clear()
        os.environ.pop("DB_PATH", None)
        os.environ.pop("DEVELOPMENT_MODE", None)
        get_settings.cache_clear()


def test_main_lifespan_runs_alembic_migration(tmp_path):
    """When no get_db override is set, the lifespan runs Alembic migrations and seeds tax config."""
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.config import get_settings
    from app.database import get_engine, get_session_factory

    db_file = str(tmp_path / "lifespan_alembic.db")
    os.environ["DB_PATH"] = db_file
    os.environ["DEVELOPMENT_MODE"] = "true"
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()

    # Create a fresh app with no dependency overrides — triggers the Alembic else-branch
    fresh_app = create_app()
    assert not fresh_app.dependency_overrides

    try:
        with TestClient(fresh_app, raise_server_exceptions=True) as c:
            resp = c.get("/docs")
            assert resp.status_code == 200
    finally:
        get_engine.cache_clear()
        get_session_factory.cache_clear()
        os.environ.pop("DB_PATH", None)
        os.environ.pop("DEVELOPMENT_MODE", None)
        get_settings.cache_clear()
