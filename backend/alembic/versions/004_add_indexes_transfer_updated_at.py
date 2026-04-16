"""add indexes, transfer updated_at, adjustment_type constraint

Revision ID: 004
Revises: 003
Create Date: 2026-04-11 09:50:45.059169

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, Sequence[str], None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add adjustment_type column to forecast_adjustments (was missing from prior migration)
    op.add_column('forecast_adjustments', sa.Column('adjustment_type', sa.String(length=20), server_default='fixed', nullable=True))

    # Add check constraint to forecast_adjustments (via batch for SQLite)
    with op.batch_alter_table("forecast_adjustments", schema=None, recreate="always") as batch_op:
        batch_op.create_check_constraint(
            "ck_adjustment_type",
            "adjustment_type IN ('fixed', 'percentage')"
        )

    # Add updated_at to transfers (via batch for SQLite — non-constant defaults require table recreation)
    # ix_transfers_user_id pre-exists from the ORM model (index=True on user_id); batch recreate preserves it.
    with op.batch_alter_table("transfers", schema=None, recreate="always") as batch_op:
        batch_op.add_column(sa.Column(
            "updated_at", sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ))

    # Create composite and single-column indexes
    op.create_index("ix_transaction_user_billing_month", "transactions", ["user_id", "billing_month"])
    op.create_index("ix_transaction_parent_id", "transactions", ["parent_transaction_id"])
    op.create_index("ix_transfer_user_billing_month", "transfers", ["user_id", "billing_month"])
    op.create_index("ix_transfer_parent_id", "transfers", ["parent_transfer_id"])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop composite indexes
    op.drop_index("ix_transfer_parent_id", table_name="transfers")
    op.drop_index("ix_transfer_user_billing_month", table_name="transfers")
    op.drop_index("ix_transaction_parent_id", table_name="transactions")
    op.drop_index("ix_transaction_user_billing_month", table_name="transactions")

    # Remove updated_at from transfers (via batch for SQLite)
    # ix_transfers_user_id pre-exists from the ORM model (index=True on user_id); batch recreate preserves it.
    with op.batch_alter_table("transfers", schema=None, recreate="always") as batch_op:
        batch_op.drop_column("updated_at")

    # Remove check constraint and adjustment_type column from forecast_adjustments
    with op.batch_alter_table("forecast_adjustments", schema=None, recreate="always") as batch_op:
        batch_op.drop_constraint("ck_adjustment_type", type_="check")
        batch_op.drop_column("adjustment_type")
