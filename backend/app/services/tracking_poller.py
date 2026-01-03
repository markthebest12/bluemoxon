"""Tracking polling service for automatic shipment status updates."""

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import Book, Notification, User
from app.services.carriers import get_carrier

logger = logging.getLogger(__name__)


def notify_status_change(
    db: Session,
    user: User,
    book: Book,
    old_status: str | None,
    new_status: str,
) -> None:
    """Create a notification for tracking status change.

    Args:
        db: Database session
        user: User to notify
        book: Book with tracking update
        old_status: Previous tracking status
        new_status: New tracking status
    """
    message = f"Tracking update for '{book.title}': {new_status}"
    notification = Notification(
        user_id=user.id,
        book_id=book.id,
        message=message,
        read=False,
    )
    db.add(notification)
    db.flush()  # Make notification visible in current transaction
    logger.info(f"Created notification for user {user.id}: {message}")


def poll_all_active_tracking(db: Session) -> dict:
    """Poll all active tracking numbers and update statuses.

    Args:
        db: Database session

    Returns:
        dict with stats: {"checked": N, "changed": N, "errors": N, "deactivated": N}
    """
    stats = {"checked": 0, "changed": 0, "errors": 0, "deactivated": 0}

    # Query books with active tracking
    active_books = (
        db.query(Book)
        .filter(
            Book.tracking_active == True,  # noqa: E712
            Book.tracking_number.isnot(None),
        )
        .all()
    )

    for book in active_books:
        stats["checked"] += 1

        try:
            carrier = get_carrier(book.tracking_carrier)
            result = carrier.fetch_tracking(book.tracking_number)

            # Check if status changed
            if result.status != book.tracking_status:
                stats["changed"] += 1
                logger.info(
                    f"Book {book.id} tracking status changed: "
                    f"{book.tracking_status} -> {result.status}"
                )
                book.tracking_status = result.status

            # Handle delivery tracking
            if result.status == "Delivered":
                if book.tracking_delivered_at is None:
                    book.tracking_delivered_at = datetime.now(UTC)
                    logger.info(f"Book {book.id} marked as delivered")
                else:
                    # Check if 7+ days since delivery - deactivate
                    delivered_at = book.tracking_delivered_at
                    if delivered_at.tzinfo is None:
                        delivered_at = delivered_at.replace(tzinfo=UTC)
                    days_since_delivery = (datetime.now(UTC) - delivered_at).days
                    if days_since_delivery >= 7:
                        book.tracking_active = False
                        stats["deactivated"] += 1
                        logger.info(
                            f"Book {book.id} tracking deactivated "
                            f"({days_since_delivery} days after delivery)"
                        )

            # Update last checked timestamp
            book.tracking_last_checked = datetime.now(UTC)

        except Exception as e:
            stats["errors"] += 1
            logger.error(f"Error polling tracking for book {book.id}: {e}")

    db.commit()
    logger.info(f"Tracking poll complete: {stats}")
    return stats


def refresh_single_book_tracking(db: Session, book_id: int) -> dict:
    """Refresh tracking status for a single book.

    Args:
        db: Database session
        book_id: ID of the book to refresh

    Returns:
        dict with tracking result info

    Raises:
        ValueError: If book not found or has no tracking number
    """
    book = db.query(Book).filter(Book.id == book_id).first()

    if book is None:
        raise ValueError(f"Book not found: {book_id}")

    if not book.tracking_number:
        raise ValueError(f"No tracking number for book {book_id}")

    previous_status = book.tracking_status

    carrier = get_carrier(book.tracking_carrier)
    result = carrier.fetch_tracking(book.tracking_number)

    # Update status
    changed = result.status != book.tracking_status
    book.tracking_status = result.status
    book.tracking_last_checked = datetime.now(UTC)

    # Activate tracking if not already active
    if not book.tracking_active:
        book.tracking_active = True

    # Handle delivery
    if result.status == "Delivered" and book.tracking_delivered_at is None:
        book.tracking_delivered_at = datetime.now(UTC)

    db.commit()

    return {
        "status": result.status,
        "status_detail": result.status_detail,
        "location": result.location,
        "estimated_delivery": result.estimated_delivery,
        "delivered_at": result.delivered_at,
        "changed": changed,
        "previous_status": previous_status,
    }
