"""add refresh tokens and login attempts

Revision ID: 9e3c1b0f6a2d
Revises: e8d2354c7107
Create Date: 2026-04-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9e3c1b0f6a2d"
down_revision: Union[str, Sequence[str], None] = "e8d2354c7107"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("jti", sa.String(length=36), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["auth.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="auth",
    )
    op.create_index(
        "ix_auth_refresh_tokens_jti",
        "refresh_tokens",
        ["jti"],
        unique=True,
        schema="auth",
    )
    op.create_index(
        "ix_auth_refresh_tokens_user_id",
        "refresh_tokens",
        ["user_id"],
        unique=False,
        schema="auth",
    )

    op.create_table(
        "login_attempts",
        sa.Column("bucket", sa.String(length=320), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("bucket"),
        schema="auth",
    )


def downgrade() -> None:
    op.drop_table("login_attempts", schema="auth")
    op.drop_index("ix_auth_refresh_tokens_user_id", table_name="refresh_tokens", schema="auth")
    op.drop_index("ix_auth_refresh_tokens_jti", table_name="refresh_tokens", schema="auth")
    op.drop_table("refresh_tokens", schema="auth")
