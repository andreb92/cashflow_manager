"""Make linked bank references nullable with SET NULL

Revision ID: 012pm_link_set_null
Revises: 011tx_pm_set_null
Create Date: 2026-05-15
"""
from alembic import op
import sqlalchemy as sa


revision = "012pm_link_set_null"
down_revision = "011tx_pm_set_null"
branch_labels = None
depends_on = None


_payment_methods_link_set_null = sa.Table(
    "payment_methods",
    sa.MetaData(),
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    sa.Column("name", sa.String(255), nullable=False),
    sa.Column("type", sa.String(50), nullable=False),
    sa.Column("is_main_bank", sa.Boolean, nullable=False, server_default="0"),
    sa.Column(
        "linked_bank_id",
        sa.String(36),
        sa.ForeignKey("payment_methods.id", name="fk_payment_methods_linked_bank_id", ondelete="SET NULL"),
        nullable=True,
    ),
    sa.Column("opening_balance", sa.Numeric(12, 2), nullable=True),
    sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
    sa.Column("has_stamp_duty", sa.Boolean, nullable=False, server_default="0"),
    sa.UniqueConstraint("user_id", "name", name="uq_pm_user_name"),
)


_payment_methods_link_restrict = sa.Table(
    "payment_methods",
    sa.MetaData(),
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    sa.Column("name", sa.String(255), nullable=False),
    sa.Column("type", sa.String(50), nullable=False),
    sa.Column("is_main_bank", sa.Boolean, nullable=False, server_default="0"),
    sa.Column("linked_bank_id", sa.String(36), sa.ForeignKey("payment_methods.id"), nullable=True),
    sa.Column("opening_balance", sa.Numeric(12, 2), nullable=True),
    sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
    sa.Column("has_stamp_duty", sa.Boolean, nullable=False, server_default="0"),
    sa.UniqueConstraint("user_id", "name", name="uq_pm_user_name"),
)


def upgrade() -> None:
    with op.batch_alter_table(
        "payment_methods",
        schema=None,
        recreate="always",
        copy_from=_payment_methods_link_set_null,
    ) as batch_op:
        batch_op.create_index("ix_payment_methods_user_id", ["user_id"])


def downgrade() -> None:
    with op.batch_alter_table(
        "payment_methods",
        schema=None,
        recreate="always",
        copy_from=_payment_methods_link_restrict,
    ) as batch_op:
        batch_op.create_index("ix_payment_methods_user_id", ["user_id"])
