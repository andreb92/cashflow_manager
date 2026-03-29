# backend/tests/test_migrations.py
import os
import tempfile
import pytest
from sqlalchemy import create_engine, inspect
from alembic import command
from alembic.config import Config


def _cfg(db_path: str) -> Config:
    """Return Alembic config pointed at a temp DB."""
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return cfg


def test_migration_head_creates_expected_schema():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        command.upgrade(_cfg(db_path), "head")
        engine = create_engine(f"sqlite:///{db_path}")
        inspector = inspect(engine)

        # transfers table
        transfer_cols = {c["name"] for c in inspector.get_columns("transfers")}
        assert "parent_transfer_id" in transfer_cols

        # salary_config table
        salary_cols = {c["name"] for c in inspector.get_columns("salary_config")}
        assert "salary_months" in salary_cols

        # tax_config table — new column names, old names gone
        tax_cols = {c["name"] for c in inspector.get_columns("tax_config")}
        assert "employment_deduction_band1_limit" in tax_cols
        assert "employment_deduction_floor" in tax_cols
        assert "user_id" in tax_cols
        assert "detrazione_band1_limit" not in tax_cols

        # payment_methods — unique constraint
        unique_constraints = {
            uc["name"] for uc in inspector.get_unique_constraints("payment_methods")
        }
        assert "uq_pm_user_name" in unique_constraints

        # forecasts — datetime columns
        forecast_cols = {c["name"]: c for c in inspector.get_columns("forecasts")}
        assert "created_at" in forecast_cols
        assert "updated_at" in forecast_cols
    finally:
        os.unlink(db_path)
