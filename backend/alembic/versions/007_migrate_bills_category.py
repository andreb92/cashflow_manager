"""Migrate Bills top-level category type to Housing

Revision ID: 007
Revises: 006
Create Date: 2026-04-18

"""
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Bills was removed as a top-level type; any remaining rows belong under Housing.
    # Rows that already have a Housing/Bills counterpart are deleted to avoid duplicates;
    # all other Bills/* rows are reparented to Housing.
    op.execute("""
        DELETE FROM categories
        WHERE type = 'Bills'
        AND (user_id, sub_type) IN (
            SELECT user_id, sub_type FROM categories WHERE type = 'Housing'
        )
    """)
    op.execute("UPDATE categories SET type = 'Housing' WHERE type = 'Bills'")


def downgrade() -> None:
    pass
