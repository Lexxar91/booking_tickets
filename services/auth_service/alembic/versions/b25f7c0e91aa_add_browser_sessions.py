"""Добавляет серверные сессии BFF с зашифрованными токенами."""

import sqlalchemy as sa
from alembic import op

revision = "b25f7c0e91aa"
down_revision = "9e3c1b0f6a2d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создает хранилище сессий и индекс срока действия."""
    op.create_table(
        "browser_sessions",
        sa.Column("id_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("csrf_token", sa.String(64), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column("access_expires_at", sa.DateTime(timezone=True),
                  nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["auth.users.id"], ondelete="CASCADE"),
        schema="auth",
    )
    op.create_index(
        "ix_auth_browser_sessions_expires_at", "browser_sessions",
        ["expires_at"], schema="auth",
    )


def downgrade() -> None:
    """Удаляет сессии BFF, сохраняя пользователей и JWT API."""
    op.drop_table("browser_sessions", schema="auth")
