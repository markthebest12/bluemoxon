"""add_carrier_api_support

Add database schema changes for carrier API support (#516):
- books: tracking_active, tracking_delivered_at columns
- users: notify_tracking_email, notify_tracking_sms, phone_number columns
- notifications: new table for in-app notifications

Revision ID: w6789012wxyz
Revises: v5678901uvwx
Create Date: 2026-01-02 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "w6789012wxyz"
down_revision: str | None = "v5678901uvwx"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add carrier API support tables and columns."""
    # Add tracking columns to books table
    op.add_column(
        "books",
        sa.Column("tracking_active", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "books",
        sa.Column("tracking_delivered_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Add notification preference columns to users table
    op.add_column(
        "users",
        sa.Column("notify_tracking_email", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "users",
        sa.Column("notify_tracking_sms", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "users",
        sa.Column("phone_number", sa.String(20), nullable=True),
    )

    # Create notifications table
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "book_id",
            sa.Integer(),
            sa.ForeignKey("books.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Create partial index for efficient unread notification queries
    # PostgreSQL supports partial indexes with WHERE clause
    op.create_index(
        "idx_notifications_user_unread",
        "notifications",
        ["user_id", "read"],
        postgresql_where=sa.text("read = false"),
    )


def downgrade() -> None:
    """Remove carrier API support tables and columns."""
    # Drop notifications table and index
    op.drop_index("idx_notifications_user_unread", table_name="notifications")
    op.drop_table("notifications")

    # Remove notification preference columns from users
    op.drop_column("users", "phone_number")
    op.drop_column("users", "notify_tracking_sms")
    op.drop_column("users", "notify_tracking_email")

    # Remove tracking columns from books
    op.drop_column("books", "tracking_delivered_at")
    op.drop_column("books", "tracking_active")
