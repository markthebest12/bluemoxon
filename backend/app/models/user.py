"""User model - Cognito user metadata."""

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """User preferences and metadata (auth handled by Cognito)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    cognito_sub: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    display_name: Mapped[str | None] = mapped_column(String(100))  # Deprecated, use first_name
    role: Mapped[str] = mapped_column(String(20), default="viewer")  # admin, editor, viewer
    mfa_exempt: Mapped[bool] = mapped_column(default=False)  # Admin can exempt users from MFA
    preferences: Mapped[dict | None] = mapped_column(JSON, default=dict)  # JSON for cross-DB

    # Notification preferences (for carrier tracking)
    notify_tracking_email: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_tracking_sms: Mapped[bool] = mapped_column(Boolean, default=False)
    phone_number: Mapped[str | None] = mapped_column(String(20))

    # Relationships
    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
