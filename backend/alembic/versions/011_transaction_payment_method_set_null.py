"""Make transaction payment method nullable with SET NULL

Revision ID: 011tx_pm_set_null
Revises: 010remove_installments
Create Date: 2026-05-15
"""
from alembic import op
import sqlalchemy as sa


revision = "011tx_pm_set_null"
down_revision = "010remove_installments"
branch_labels = None
depends_on = None


_transactions_pm_set_null = sa.Table(
    "transactions",
    sa.MetaData(),
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    sa.Column("date", sa.String(10), nullable=False),
    sa.Column("detail", sa.String(500), nullable=False),
    sa.Column("amount", sa.Numeric(12, 2), nullable=False),
    sa.Column(
        "payment_method_id",
        sa.String(36),
        sa.ForeignKey("payment_methods.id", name="fk_transactions_payment_method_id", ondelete="SET NULL"),
        nullable=True,
    ),
    sa.Column(
        "category_id",
        sa.String(36),
        sa.ForeignKey("categories.id", name="fk_transactions_category_id", ondelete="RESTRICT"),
        nullable=True,
    ),
    sa.Column("transaction_direction", sa.String(20), nullable=False),
    sa.Column("billing_month", sa.String(10), nullable=False),
    sa.Column("recurrence_months", sa.Integer, nullable=True),
    sa.Column("parent_transaction_id", sa.String(36), sa.ForeignKey("transactions.id"), nullable=True),
    sa.Column("notes", sa.Text, nullable=True),
    sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
)


_transactions_pm_required = sa.Table(
    "transactions",
    sa.MetaData(),
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    sa.Column("date", sa.String(10), nullable=False),
    sa.Column("detail", sa.String(500), nullable=False),
    sa.Column("amount", sa.Numeric(12, 2), nullable=False),
    sa.Column("payment_method_id", sa.String(36), sa.ForeignKey("payment_methods.id"), nullable=False),
    sa.Column(
        "category_id",
        sa.String(36),
        sa.ForeignKey("categories.id", name="fk_transactions_category_id", ondelete="RESTRICT"),
        nullable=True,
    ),
    sa.Column("transaction_direction", sa.String(20), nullable=False),
    sa.Column("billing_month", sa.String(10), nullable=False),
    sa.Column("recurrence_months", sa.Integer, nullable=True),
    sa.Column("parent_transaction_id", sa.String(36), sa.ForeignKey("transactions.id"), nullable=True),
    sa.Column("notes", sa.Text, nullable=True),
    sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
)


def _recreate_indexes(batch_op) -> None:
    batch_op.create_index("ix_transactions_user_id", ["user_id"])
    batch_op.create_index("ix_transaction_user_billing_month", ["user_id", "billing_month"])
    batch_op.create_index("ix_transaction_parent_id", ["parent_transaction_id"])
    batch_op.create_index("ix_transaction_user_date", ["user_id", "date"])


def upgrade() -> None:
    with op.batch_alter_table(
        "transactions",
        schema=None,
        recreate="always",
        copy_from=_transactions_pm_set_null,
    ) as batch_op:
        _recreate_indexes(batch_op)


def downgrade() -> None:
    with op.batch_alter_table(
        "transactions",
        schema=None,
        recreate="always",
        copy_from=_transactions_pm_required,
    ) as batch_op:
        _recreate_indexes(batch_op)
