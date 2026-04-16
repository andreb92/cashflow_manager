"""Remove Transfer, Inv-Transfer, Inv-Outcome seed categories

Revision ID: 006
Revises: 005
Create Date: 2026-04-18

"""
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DELETE FROM categories
        WHERE sub_type IN ('Transfer', 'Inv-Transfer', 'Inv-Outcome')
        AND id NOT IN (
            SELECT category_id FROM transactions WHERE category_id IS NOT NULL
        )
    """)


def downgrade() -> None:
    pass
