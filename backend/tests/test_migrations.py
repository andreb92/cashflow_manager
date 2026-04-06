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

        # transactions — category_id FK must have exactly one reference to categories with RESTRICT
        tx_fks = inspector.get_foreign_keys("transactions")
        cat_fks = [fk for fk in tx_fks if fk["referred_table"] == "categories"]
        assert len(cat_fks) == 1, f"Expected 1 FK to categories, got {len(cat_fks)}: {cat_fks}"
        assert cat_fks[0]["options"].get("ondelete", "").upper() == "RESTRICT", (
            f"Expected RESTRICT ondelete on transactions.category_id, got: {cat_fks[0]}"
        )

        # main_bank_history FK must have exactly one reference to payment_methods with CASCADE
        fks = inspector.get_foreign_keys("main_bank_history")
        pm_fks = [fk for fk in fks if fk["referred_table"] == "payment_methods"]
        assert len(pm_fks) == 1, f"Expected 1 FK to payment_methods, got {len(pm_fks)}: {pm_fks}"
        assert pm_fks[0]["options"]["ondelete"].upper() == "CASCADE", f"Expected CASCADE ondelete, got: {pm_fks[0]}"

        # main_bank_history — user_id index must survive the batch rebuild in 003
        mbh_index_names = {idx["name"] for idx in inspector.get_indexes("main_bank_history")}
        assert "ix_main_bank_history_user_id" in mbh_index_names, (
            f"ix_main_bank_history_user_id missing from main_bank_history. Found: {mbh_index_names}"
        )
    finally:
        os.unlink(db_path)


def test_migration_003_roundtrip_preserves_user_id_index():
    """Downgrade to 002 then re-upgrade to head must preserve ix_main_bank_history_user_id."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        command.upgrade(_cfg(db_path), "head")
        command.downgrade(_cfg(db_path), "002")
        command.upgrade(_cfg(db_path), "head")

        engine = create_engine(f"sqlite:///{db_path}")
        inspector = inspect(engine)
        index_names = {idx["name"] for idx in inspector.get_indexes("main_bank_history")}
        assert "ix_main_bank_history_user_id" in index_names, (
            f"ix_main_bank_history_user_id missing after downgrade+upgrade. Found: {index_names}"
        )
    finally:
        command.downgrade(_cfg(db_path), "base")
        os.unlink(db_path)
