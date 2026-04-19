"""Add from/to_payment_method_id FKs to transfers

Revision ID: 008
Revises: 007
Create Date: 2026-04-18

Adds nullable FK columns ``from_payment_method_id`` and ``to_payment_method_id``
to the ``transfers`` table so bank-side transfer matching can use a stable id
rather than the (mutable) PaymentMethod name. Backfills the new columns from
existing rows by matching ``(user_id, name)`` for rows where the corresponding
account type is ``bank``.
"""
from alembic import op
import sqlalchemy as sa


revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite does not support adding columns with FK constraints inline via
    # plain ALTER TABLE — batch_alter_table recreates the table so the FK is
    # preserved.
    with op.batch_alter_table("transfers", schema=None, recreate="always") as batch_op:
        batch_op.add_column(sa.Column("from_payment_method_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("to_payment_method_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_transfers_from_pm_id", "payment_methods",
            ["from_payment_method_id"], ["id"], ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_transfers_to_pm_id", "payment_methods",
            ["to_payment_method_id"], ["id"], ondelete="SET NULL",
        )

    # Data backfill — only bank-side accounts map to payment_methods rows.
    # saving / investment / pension sides have no PM record; leave them NULL.
    op.execute("""
        UPDATE transfers
        SET from_payment_method_id = (
            SELECT pm.id FROM payment_methods pm
            WHERE pm.user_id = transfers.user_id
              AND pm.name = transfers.from_account_name
        )
        WHERE from_account_type = 'bank'
    """)
    op.execute("""
        UPDATE transfers
        SET to_payment_method_id = (
            SELECT pm.id FROM payment_methods pm
            WHERE pm.user_id = transfers.user_id
              AND pm.name = transfers.to_account_name
        )
        WHERE to_account_type = 'bank'
    """)


def downgrade() -> None:
    with op.batch_alter_table("transfers", schema=None, recreate="always") as batch_op:
        batch_op.drop_constraint("fk_transfers_to_pm_id", type_="foreignkey")
        batch_op.drop_constraint("fk_transfers_from_pm_id", type_="foreignkey")
        batch_op.drop_column("to_payment_method_id")
        batch_op.drop_column("from_payment_method_id")
