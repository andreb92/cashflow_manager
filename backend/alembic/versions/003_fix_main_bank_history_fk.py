"""Fix MainBankHistory payment_method_id FK (CASCADE) and Transaction category_id FK (RESTRICT)

Revision ID: 003
Revises: 002
Create Date: 2026-04-05

"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None

# Explicit table definition used as the copy_from source so that batch_alter_table
# builds the new table from this spec rather than reflecting the live table.
# This discards the original anonymous FK (no ondelete) from migration 001 and
# replaces it with a single named FK with ON DELETE CASCADE, preventing duplicate
# FK constraints on the same column.
_main_bank_history_with_cascade = sa.Table(
    "main_bank_history",
    sa.MetaData(),
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column(
        "user_id",
        sa.String(36),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column(
        "payment_method_id",
        sa.String(36),
        sa.ForeignKey(
            "payment_methods.id",
            name="fk_main_bank_history_payment_method_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    ),
    sa.Column("valid_from", sa.String(10), nullable=False),
    sa.Column("opening_balance", sa.Numeric(12, 2), nullable=False, server_default="0"),
)

# Explicit table spec for transactions: upgrade target (category_id has RESTRICT).
# payment_method_id matches migration 001 (nullable=False, no ondelete) to avoid
# accidentally changing that column's constraint in this migration.
_transactions_with_restrict = sa.Table(
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
    sa.Column("installment_total", sa.Integer, nullable=True),
    sa.Column("installment_index", sa.Integer, nullable=True),
    sa.Column("parent_transaction_id", sa.String(36), sa.ForeignKey("transactions.id"), nullable=True),
    sa.Column("notes", sa.Text, nullable=True),
    sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
)

# Downgrade target for transactions: category_id FK without ondelete clause.
_transactions_no_restrict = sa.Table(
    "transactions",
    sa.MetaData(),
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
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

# Downgrade target: same table but without ondelete on the payment_method FK.
_main_bank_history_no_cascade = sa.Table(
    "main_bank_history",
    sa.MetaData(),
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column(
        "user_id",
        sa.String(36),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column(
        "payment_method_id",
        sa.String(36),
        sa.ForeignKey("payment_methods.id"),
        nullable=False,
    ),
    sa.Column("valid_from", sa.String(10), nullable=False),
    sa.Column("opening_balance", sa.Numeric(12, 2), nullable=False, server_default="0"),
)


def upgrade() -> None:
    # copy_from supplies the exact target schema; recreate="always" forces a full
    # table rebuild.  Together they guarantee only the FKs declared in
    # _main_bank_history_with_cascade end up in the new table — no duplicate,
    # anonymous FK carried forward from migration 001.
    with op.batch_alter_table(
        "main_bank_history",
        schema=None,
        recreate="always",
        copy_from=_main_bank_history_with_cascade,
    ) as batch_op:
        # index=True on a copy_from column spec is a no-op in Alembic;
        # the index must be created explicitly after the batch rebuild.
        # recreate="always" drops the old table+index; create_index is always safe here.
        batch_op.create_index("ix_main_bank_history_user_id", ["user_id"])

    # Same pattern for transactions: rebuild with category_id FK gaining RESTRICT.
    with op.batch_alter_table(
        "transactions",
        schema=None,
        recreate="always",
        copy_from=_transactions_with_restrict,
    ) as batch_op:
        batch_op.create_index("ix_transactions_user_id", ["user_id"])


def downgrade() -> None:
    # Reverse transactions: rebuild without RESTRICT on category_id FK.
    with op.batch_alter_table(
        "transactions",
        schema=None,
        recreate="always",
        copy_from=_transactions_no_restrict,
    ) as batch_op:
        batch_op.create_index("ix_transactions_user_id", ["user_id"])

    # Reverse: rebuild without the ondelete clause on payment_method_id.
    with op.batch_alter_table(
        "main_bank_history",
        schema=None,
        recreate="always",
        copy_from=_main_bank_history_no_cascade,
    ) as batch_op:
        # recreate="always" drops the old table+index; create_index is always safe here.
        batch_op.create_index("ix_main_bank_history_user_id", ["user_id"])
