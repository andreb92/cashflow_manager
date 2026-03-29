"""Initial schema — all tables at v1.0.0

Revision ID: 001
Revises:
Create Date: 2026-03-29

NOTE: If migrating an existing database that was previously at revision 005,
run: alembic stamp 001
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=True),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("oidc_sub", sa.String(255), unique=True, nullable=True),
        sa.Column("name", sa.String(255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_table(
        "user_settings",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("key", sa.String(255), primary_key=True),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_table(
        "payment_methods",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("is_main_bank", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("linked_bank_id", sa.String(36), sa.ForeignKey("payment_methods.id"), nullable=True),
        sa.Column("opening_balance", sa.Numeric(12, 2), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.UniqueConstraint("user_id", "name", name="uq_pm_user_name"),
    )
    op.create_table(
        "main_bank_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("payment_method_id", sa.String(36), sa.ForeignKey("payment_methods.id"), nullable=False),
        sa.Column("valid_from", sa.String(10), nullable=False),
        sa.Column("opening_balance", sa.Numeric(12, 2), nullable=False, server_default="0"),
    )
    op.create_table(
        "categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("type", sa.String(255), nullable=False),
        sa.Column("sub_type", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
    )
    op.create_table(
        "transactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("date", sa.String(10), nullable=False),
        sa.Column("detail", sa.String(500), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_method_id", sa.String(36), sa.ForeignKey("payment_methods.id"), nullable=False),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("transaction_direction", sa.String(20), nullable=False),
        sa.Column("billing_month", sa.String(10), nullable=False),
        sa.Column("recurrence_months", sa.Integer, nullable=True),
        sa.Column("installment_total", sa.Integer, nullable=True),
        sa.Column("installment_index", sa.Integer, nullable=True),
        sa.Column("parent_transaction_id", sa.String(36), sa.ForeignKey("transactions.id"), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_table(
        "transfers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("date", sa.String(10), nullable=False),
        sa.Column("detail", sa.String(500), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("from_account_type", sa.String(20), nullable=False),
        sa.Column("from_account_name", sa.String(255), nullable=False),
        sa.Column("to_account_type", sa.String(20), nullable=False),
        sa.Column("to_account_name", sa.String(255), nullable=False),
        sa.Column("billing_month", sa.String(10), nullable=False),
        sa.Column("recurrence_months", sa.Integer, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("parent_transfer_id", sa.String(36), sa.ForeignKey("transfers.id"), nullable=True),
    )
    op.create_table(
        "assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("asset_type", sa.String(20), nullable=False),
        sa.Column("asset_name", sa.String(255), nullable=False),
        sa.Column("manual_override", sa.Numeric(12, 2), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_table(
        "salary_config",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("valid_from", sa.String(10), nullable=False),
        sa.Column("ral", sa.Numeric(12, 2), nullable=False),
        sa.Column("employer_contrib_rate", sa.Numeric(6, 4), nullable=False, server_default="0.04"),
        sa.Column("voluntary_contrib_rate", sa.Numeric(6, 4), nullable=False, server_default="0.0"),
        sa.Column("regional_tax_rate", sa.Numeric(6, 4), nullable=False, server_default="0.0173"),
        sa.Column("municipal_tax_rate", sa.Numeric(6, 4), nullable=False, server_default="0.001"),
        sa.Column("meal_vouchers_annual", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("welfare_annual", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("manual_net_override", sa.Numeric(10, 2), nullable=True),
        sa.Column("computed_net_monthly", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("salary_months", sa.Integer, nullable=False, server_default="12"),
    )
    op.create_table(
        "tax_config",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("valid_from", sa.String(10), nullable=False),
        sa.Column("inps_rate", sa.Numeric(6, 4), nullable=False, server_default="0.0919"),
        sa.Column("irpef_band1_rate", sa.Numeric(6, 4), nullable=False, server_default="0.23"),
        sa.Column("irpef_band1_limit", sa.Numeric(10, 2), nullable=False, server_default="28000"),
        sa.Column("irpef_band2_rate", sa.Numeric(6, 4), nullable=False, server_default="0.33"),
        sa.Column("irpef_band2_limit", sa.Numeric(10, 2), nullable=False, server_default="50000"),
        sa.Column("irpef_band3_rate", sa.Numeric(6, 4), nullable=False, server_default="0.43"),
        sa.Column("employment_deduction_band1_limit", sa.Numeric(10, 2), nullable=False, server_default="15000"),
        sa.Column("employment_deduction_band1_amount", sa.Numeric(10, 2), nullable=False, server_default="1955"),
        sa.Column("employment_deduction_band2_limit", sa.Numeric(10, 2), nullable=False, server_default="28000"),
        sa.Column("employment_deduction_band2_base", sa.Numeric(10, 2), nullable=False, server_default="1910"),
        sa.Column("employment_deduction_band2_variable", sa.Numeric(10, 2), nullable=False, server_default="1190"),
        sa.Column("employment_deduction_band2_range", sa.Numeric(10, 2), nullable=False, server_default="13000"),
        sa.Column("employment_deduction_band3_limit", sa.Numeric(10, 2), nullable=False, server_default="50000"),
        sa.Column("employment_deduction_band3_base", sa.Numeric(10, 2), nullable=False, server_default="1910"),
        sa.Column("employment_deduction_band3_range", sa.Numeric(10, 2), nullable=False, server_default="22000"),
        sa.Column("pension_deductibility_cap", sa.Numeric(10, 2), nullable=False, server_default="5164.57"),
        sa.Column("employment_deduction_floor", sa.Numeric(10, 2), nullable=False, server_default="690.00"),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True),
    )
    op.create_table(
        "forecasts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("base_year", sa.Integer, nullable=False),
        sa.Column("projection_years", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_table(
        "forecast_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("forecast_id", sa.String(36), sa.ForeignKey("forecasts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("source_transaction_id", sa.String(36), sa.ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("detail", sa.Text, nullable=False),
        sa.Column("base_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_method_id", sa.String(36), sa.ForeignKey("payment_methods.id", ondelete="SET NULL"), nullable=True),
        sa.Column("billing_day", sa.Integer, nullable=False, server_default="1"),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_table(
        "forecast_adjustments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("forecast_line_id", sa.String(36), sa.ForeignKey("forecast_lines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("valid_from", sa.String(10), nullable=False),
        sa.Column("new_amount", sa.Numeric(12, 2), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("forecast_adjustments")
    op.drop_table("forecast_lines")
    op.drop_table("forecasts")
    op.drop_table("tax_config")
    op.drop_table("salary_config")
    op.drop_table("assets")
    op.drop_table("transfers")
    op.drop_table("transactions")
    op.drop_table("categories")
    op.drop_table("main_bank_history")
    op.drop_table("payment_methods")
    op.drop_table("user_settings")
    op.drop_table("users")
