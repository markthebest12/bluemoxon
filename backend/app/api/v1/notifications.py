"""Notifications API endpoints."""

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.db import get_db
from app.models.user import User
from app.services.notifications import (
    get_unread_count,
    get_user_notifications,
    mark_notification_read,
)

# E.164 phone number format: + followed by 1-15 digits
E164_PATTERN = re.compile(r"^\+[1-9]\d{1,14}$")

router = APIRouter()


class NotificationResponse(BaseModel):
    """Notification response schema."""

    id: int
    user_id: int
    book_id: int | None
    message: str
    read: bool
    created_at: str

    model_config = {"from_attributes": True}


class NotificationsListResponse(BaseModel):
    """Response for listing notifications."""

    items: list[NotificationResponse]
    unread_count: int


class UpdatePreferencesRequest(BaseModel):
    """Request to update notification preferences."""

    notify_tracking_email: bool | None = None
    notify_tracking_sms: bool | None = None
    phone_number: str | None = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str | None) -> str | None:
        """Validate phone number is E.164 format if provided."""
        if v is None or v == "":
            return None
        if not E164_PATTERN.match(v):
            raise ValueError("Phone number must be in E.164 format (e.g., +14155551234)")
        return v


class PreferencesResponse(BaseModel):
    """Response with notification preferences."""

    notify_tracking_email: bool
    notify_tracking_sms: bool
    phone_number: str | None


@router.get("/notifications", response_model=NotificationsListResponse)
async def list_notifications(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Get notifications for the current user.

    Returns paginated list of notifications ordered by most recent first,
    along with the total count of unread notifications.
    """
    if not current_user.db_user:
        raise HTTPException(status_code=404, detail="User not found")

    notifications = get_user_notifications(
        db=db,
        user_id=current_user.db_user.id,
        limit=limit,
        offset=offset,
    )

    unread = get_unread_count(db=db, user_id=current_user.db_user.id)

    return {
        "items": [
            {
                "id": n.id,
                "user_id": n.user_id,
                "book_id": n.book_id,
                "message": n.message,
                "read": n.read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifications
        ],
        "unread_count": unread,
    }


@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Mark a notification as read.

    Only the notification owner can mark it as read.
    """
    if not current_user.db_user:
        raise HTTPException(status_code=404, detail="User not found")

    success = mark_notification_read(
        db=db,
        notification_id=notification_id,
        user_id=current_user.db_user.id,
    )

    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")

    # Re-fetch the notification to return updated state
    from app.models.notification import Notification

    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.db_user.id,
        )
        .first()
    )

    return {
        "id": notification.id,
        "user_id": notification.user_id,
        "book_id": notification.book_id,
        "message": notification.message,
        "read": notification.read,
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
    }


@router.patch("/preferences", response_model=PreferencesResponse)
async def update_preferences(
    request: UpdatePreferencesRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Update notification preferences for the current user.

    Supports partial updates - only provided fields will be changed.
    """
    if not current_user.db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Re-fetch user to ensure we have latest data
    user = db.query(User).filter(User.id == current_user.db_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update only provided fields
    if request.notify_tracking_email is not None:
        user.notify_tracking_email = request.notify_tracking_email
    if request.notify_tracking_sms is not None:
        user.notify_tracking_sms = request.notify_tracking_sms
    if request.phone_number is not None:
        user.phone_number = request.phone_number

    db.commit()
    db.refresh(user)

    return {
        "notify_tracking_email": user.notify_tracking_email,
        "notify_tracking_sms": user.notify_tracking_sms,
        "phone_number": user.phone_number,
    }
