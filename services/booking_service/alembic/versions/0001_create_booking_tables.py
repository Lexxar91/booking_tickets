"""Создает таблицы бронирований и счетчиков билетов."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создает таблицы и индексы в схеме booking."""
    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING", "CONFIRMED", "CANCELLED",
                name="bookingstatus", schema="booking",
            ),
            nullable=False,
        ),
        sa.Column("price_at_booking", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        schema="booking",
    )
    op.create_index(
        "ix_booking_bookings_user_id", "bookings", ["user_id"],
        schema="booking",
    )
    op.create_index(
        "ix_booking_bookings_event_id", "bookings", ["event_id"],
        schema="booking",
    )
    op.create_table(
        "event_tickets",
        sa.Column("event_id", sa.Integer(), primary_key=True),
        sa.Column("available_tickets", sa.Integer(), nullable=False),
        schema="booking",
    )


def downgrade() -> None:
    """Удаляет таблицы Booking Service и тип статуса."""
    op.drop_table("event_tickets", schema="booking")
    op.drop_index(
        "ix_booking_bookings_event_id", table_name="bookings",
        schema="booking",
    )
    op.drop_index(
        "ix_booking_bookings_user_id", table_name="bookings",
        schema="booking",
    )
    op.drop_table("bookings", schema="booking")
    sa.Enum(name="bookingstatus", schema="booking").drop(op.get_bind())
