"""Remove obsolete transaction installment columns

Revision ID: 010remove_installments
Revises: 009add_transaction_date_index
Create Date: 2026-05-06
"""
from alembic import op
import sqlalchemy as sa


revision = "010remove_installments"
down_revision = "009add_transaction_date_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.drop_column("installment_total")
        batch_op.drop_column("installment_index")


def downgrade() -> None:
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.add_column(sa.Column("installment_total", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("installment_index", sa.Integer(), nullable=True))
