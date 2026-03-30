import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base
from app.deps import get_db
from app.config import get_settings
from app.models.tax import TaxConfig


def _make_client():
    # StaticPool ensures all connections share the same in-memory DB
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

    # Set before TestClient.__enter__ so lifespan sees it when
    # warn_insecure_defaults() runs at startup.
    os.environ["DEVELOPMENT_MODE"] = "true"
    get_settings.cache_clear()

    app.dependency_overrides[get_db] = override
    return TestClient(app, raise_server_exceptions=True), Session


def test_docs_endpoint():
    client, _ = _make_client()
    with client:
        resp = client.get("/docs")
        assert resp.status_code == 200
    app.dependency_overrides.clear()
    os.environ.pop("DEVELOPMENT_MODE", None)
    get_settings.cache_clear()


def test_tax_config_seeded():
    client, Session = _make_client()
    with client:
        client.get("/docs")
        db = Session()
        tc = db.query(TaxConfig).first()
        assert tc is not None
        assert abs(float(tc.inps_rate) - 0.0919) < 1e-4
        db.close()
    app.dependency_overrides.clear()
    os.environ.pop("DEVELOPMENT_MODE", None)
    get_settings.cache_clear()
