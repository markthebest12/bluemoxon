"""Notifications service for tracking updates and alerts."""

import logging

import boto3
from botocore.exceptions import ClientError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.book import Book
from app.models.notification import Notification
from app.models.user import User

logger = logging.getLogger(__name__)
settings = get_settings()


def create_in_app_notification(
    db: Session,
    user_id: int,
    message: str,
    book_id: int | None = None,
) -> Notification:
    """
    Create an in-app notification for a user.

    Args:
        db: Database session
        user_id: ID of the user to notify
        message: Notification message
        book_id: Optional book ID to associate with notification

    Returns:
        The created Notification object
    """
    notification = Notification(
        user_id=user_id,
        book_id=book_id,
        message=message,
        read=False,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def send_email_notification(user: User, message: str) -> bool:
    """
    Send email notification via AWS SES.

    Args:
        user: User to send email to
        message: Email body message

    Returns:
        True if email was sent, False if skipped
    """
    # Skip if user has email notifications disabled
    if not user.notify_tracking_email:
        logger.debug(f"Email notifications disabled for user {user.id}")
        return False

    # Skip if user has no email
    if not user.email:
        logger.debug(f"No email address for user {user.id}")
        return False

    try:
        ses = boto3.client("ses", region_name=settings.aws_region)
        ses.send_email(
            Source=settings.notification_from_email or "noreply@bluemoxon.com",
            Destination={"ToAddresses": [user.email]},
            Message={
                "Subject": {"Data": "BlueMoxon Tracking Update"},
                "Body": {
                    "Text": {"Data": message},
                },
            },
        )
        logger.info(f"Sent email notification to {user.email}")
        return True
    except ClientError as e:
        logger.error(f"Failed to send email to {user.email}: {e}")
        return False


def send_sms_notification(user: User, message: str) -> bool:
    """
    Send SMS notification via AWS SNS.

    Args:
        user: User to send SMS to
        message: SMS message

    Returns:
        True if SMS was sent, False if skipped
    """
    # Skip if user has SMS notifications disabled
    if not user.notify_tracking_sms:
        logger.debug(f"SMS notifications disabled for user {user.id}")
        return False

    # Skip if user has no phone number
    if not user.phone_number:
        logger.debug(f"No phone number for user {user.id}")
        return False

    try:
        sns = boto3.client("sns", region_name=settings.aws_region)
        sns.publish(
            PhoneNumber=user.phone_number,
            Message=message,
        )
        logger.info(f"Sent SMS notification to {user.phone_number}")
        return True
    except ClientError as e:
        logger.error(f"Failed to send SMS to {user.phone_number}: {e}")
        return False


def send_tracking_notification(
    db: Session,
    user: User,
    book: Book,
    old_status: str,
    new_status: str,
    detail: str | None = None,
) -> None:
    """
    Send tracking notification to user via all enabled channels.

    This is the main entry point for tracking notifications. It:
    1. Always creates an in-app notification
    2. Sends email if user has email notifications enabled
    3. Sends SMS if user has SMS notifications enabled

    Args:
        db: Database session
        user: User to notify
        book: Book that tracking status changed for
        old_status: Previous tracking status
        new_status: New tracking status
        detail: Optional detail message (e.g., exception reason)
    """
    # Format message based on status
    if new_status.lower() == "delivered":
        message = f"Your book '{book.title}' has been delivered!"
    elif new_status.lower() == "exception":
        detail_text = f": {detail}" if detail else ""
        message = f"Alert: '{book.title}' shipment exception{detail_text}"
    else:
        message = f"Your book '{book.title}' is now: {new_status}"

    # Always create in-app notification
    create_in_app_notification(
        db=db,
        user_id=user.id,
        book_id=book.id,
        message=message,
    )

    # Send email if enabled
    send_email_notification(user=user, message=message)

    # Send SMS if enabled
    send_sms_notification(user=user, message=message)

    logger.info(
        f"Sent tracking notification for book {book.id} to user {user.id}: "
        f"{old_status} -> {new_status}"
    )


def get_user_notifications(
    db: Session,
    user_id: int,
    limit: int = 20,
    offset: int = 0,
) -> list[Notification]:
    """
    Get notifications for a user with pagination.

    Args:
        db: Database session
        user_id: ID of user to get notifications for
        limit: Maximum number of notifications to return
        offset: Number of notifications to skip

    Returns:
        List of notifications ordered by created_at descending
    """
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def mark_notification_read(
    db: Session,
    notification_id: int,
    user_id: int,
) -> bool:
    """
    Mark a notification as read.

    Args:
        db: Database session
        notification_id: ID of notification to mark as read
        user_id: ID of user (for authorization check)

    Returns:
        True if notification was marked as read, False otherwise
    """
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        .first()
    )

    if not notification:
        return False

    notification.read = True
    db.commit()
    return True


def get_unread_count(db: Session, user_id: int) -> int:
    """
    Get count of unread notifications for a user.

    Args:
        db: Database session
        user_id: ID of user to count notifications for

    Returns:
        Count of unread notifications
    """
    return (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.read == False,  # noqa: E712
        )
        .count()
    )
