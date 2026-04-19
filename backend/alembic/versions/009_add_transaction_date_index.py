"""Add composite index on (user_id, date) for transactions

Revision ID: 009add_transaction_date_index
Revises: 008
Create Date: 2026-04-18

Adds index ix_transaction_user_date on transactions(user_id, date) to avoid
full table scans when filtering by actual transaction date (date_month filter).
"""
from alembic import op

revision = "009add_transaction_date_index"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_transaction_user_date",
        "transactions",
        ["user_id", "date"],
    )


def downgrade() -> None:
    op.drop_index("ix_transaction_user_date", table_name="transactions")
