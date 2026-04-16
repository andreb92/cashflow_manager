"""Add FK with CASCADE delete to UserSetting.user_id

Revision ID: 005
Revises: 004
Create Date: 2026-04-18

"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None

# Target schema: user_id has a named FK with ON DELETE CASCADE.
_user_settings_with_fk = sa.Table(
    "user_settings",
    sa.MetaData(),
    sa.Column(
        "user_id",
        sa.String(36),
        sa.ForeignKey("users.id", name="fk_user_settings_user_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    sa.Column("key", sa.String(255), primary_key=True),
    sa.Column("value", sa.Text, nullable=False),
    sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
)

# Downgrade target: same table without FK on user_id.
_user_settings_without_fk = sa.Table(
    "user_settings",
    sa.MetaData(),
    sa.Column("user_id", sa.String(36), primary_key=True),
    sa.Column("key", sa.String(255), primary_key=True),
    sa.Column("value", sa.Text, nullable=False),
    sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
)


def upgrade() -> None:
    with op.batch_alter_table(
        "user_settings",
        schema=None,
        recreate="always",
        copy_from=_user_settings_with_fk,
    ) as batch_op:
        pass


def downgrade() -> None:
    with op.batch_alter_table(
        "user_settings",
        schema=None,
        recreate="always",
        copy_from=_user_settings_without_fk,
    ) as batch_op:
        pass
