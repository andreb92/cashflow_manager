"""Add has_stamp_duty to payment_methods

Revision ID: 002
Revises: 001
Create Date: 2026-03-31

"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payment_methods",
        sa.Column("has_stamp_duty", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.execute("UPDATE payment_methods SET has_stamp_duty = 0")


def downgrade() -> None:
    op.drop_column("payment_methods", "has_stamp_duty")
