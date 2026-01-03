"""Notification model - In-app notifications for users."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Notification(Base):
    """In-app notification for tracking updates and other events."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    book_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("books.id", ondelete="SET NULL"),
        nullable=True,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="notifications")
    book = relationship("Book", back_populates="notifications")

    __table_args__ = (
        # Partial index for unread notifications per user (efficient for notification badge)
        Index(
            "idx_notifications_user_unread",
            "user_id",
            "read",
            postgresql_where=(~read),  # Partial index WHERE read = FALSE
        ),
    )
