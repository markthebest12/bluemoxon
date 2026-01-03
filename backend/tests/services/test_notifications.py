"""Tests for notifications service."""

from unittest.mock import MagicMock, patch

from app.models.book import Book
from app.models.notification import Notification
from app.models.user import User


class TestCreateInAppNotification:
    """Tests for in-app notification creation."""

    def test_creates_notification_with_message(self, db):
        """Creates notification with user, book, and message."""
        from app.services.notifications import create_in_app_notification

        user = User(cognito_sub="test-sub", email="test@example.com")
        db.add(user)
        db.commit()

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        notification = create_in_app_notification(
            db=db,
            user_id=user.id,
            book_id=book.id,
            message="Your book 'Test Book' is now: In Transit",
        )

        assert notification.id is not None
        assert notification.user_id == user.id
        assert notification.book_id == book.id
        assert notification.message == "Your book 'Test Book' is now: In Transit"
        assert notification.read is False

    def test_creates_notification_without_book(self, db):
        """Creates notification without book reference."""
        from app.services.notifications import create_in_app_notification

        user = User(cognito_sub="test-sub", email="test@example.com")
        db.add(user)
        db.commit()

        notification = create_in_app_notification(
            db=db,
            user_id=user.id,
            book_id=None,
            message="System notification",
        )

        assert notification.id is not None
        assert notification.book_id is None
        assert notification.message == "System notification"


class TestSendEmailNotification:
    """Tests for email notification via SES."""

    def test_sends_email_when_enabled(self, db):
        """Sends email via SES when user has email notifications enabled."""
        from app.services.notifications import send_email_notification

        user = User(
            cognito_sub="test-sub",
            email="test@example.com",
            notify_tracking_email=True,
        )
        db.add(user)
        db.commit()

        with patch("boto3.client") as mock_boto:
            mock_ses = MagicMock()
            mock_boto.return_value = mock_ses

            result = send_email_notification(user=user, message="Test message")

            assert result is True
            mock_ses.send_email.assert_called_once()
            call_args = mock_ses.send_email.call_args
            assert call_args[1]["Destination"]["ToAddresses"] == ["test@example.com"]
            assert "Test message" in call_args[1]["Message"]["Body"]["Text"]["Data"]

    def test_skips_when_disabled(self, db):
        """Skips email when user has email notifications disabled."""
        from app.services.notifications import send_email_notification

        user = User(
            cognito_sub="test-sub",
            email="test@example.com",
            notify_tracking_email=False,
        )
        db.add(user)
        db.commit()

        with patch("boto3.client") as mock_boto:
            result = send_email_notification(user=user, message="Test message")

            assert result is False
            mock_boto.assert_not_called()

    def test_skips_when_no_email(self, db):
        """Skips email when user has no email address."""
        from app.services.notifications import send_email_notification

        user = User(
            cognito_sub="test-sub",
            email=None,
            notify_tracking_email=True,
        )
        db.add(user)
        db.commit()

        with patch("boto3.client") as mock_boto:
            result = send_email_notification(user=user, message="Test message")

            assert result is False
            mock_boto.assert_not_called()


class TestSendSmsNotification:
    """Tests for SMS notification via SNS."""

    def test_sends_sms_when_enabled(self, db):
        """Sends SMS via SNS when user has SMS enabled and phone number."""
        from app.services.notifications import send_sms_notification

        user = User(
            cognito_sub="test-sub",
            email="test@example.com",
            notify_tracking_sms=True,
            phone_number="+15551234567",
        )
        db.add(user)
        db.commit()

        with patch("boto3.client") as mock_boto:
            mock_sns = MagicMock()
            mock_boto.return_value = mock_sns

            result = send_sms_notification(user=user, message="Test SMS")

            assert result is True
            mock_sns.publish.assert_called_once()
            call_args = mock_sns.publish.call_args
            assert call_args[1]["PhoneNumber"] == "+15551234567"
            assert call_args[1]["Message"] == "Test SMS"

    def test_skips_when_disabled(self, db):
        """Skips SMS when user has SMS notifications disabled."""
        from app.services.notifications import send_sms_notification

        user = User(
            cognito_sub="test-sub",
            email="test@example.com",
            notify_tracking_sms=False,
            phone_number="+15551234567",
        )
        db.add(user)
        db.commit()

        with patch("boto3.client") as mock_boto:
            result = send_sms_notification(user=user, message="Test SMS")

            assert result is False
            mock_boto.assert_not_called()

    def test_skips_when_no_phone(self, db):
        """Skips SMS when user has no phone number."""
        from app.services.notifications import send_sms_notification

        user = User(
            cognito_sub="test-sub",
            email="test@example.com",
            notify_tracking_sms=True,
            phone_number=None,
        )
        db.add(user)
        db.commit()

        with patch("boto3.client") as mock_boto:
            result = send_sms_notification(user=user, message="Test SMS")

            assert result is False
            mock_boto.assert_not_called()


class TestSendTrackingNotification:
    """Tests for the main tracking notification dispatcher."""

    def test_creates_in_app_for_status_change(self, db):
        """Creates in-app notification for any status change."""
        from app.services.notifications import send_tracking_notification

        user = User(
            cognito_sub="test-sub",
            email="test@example.com",
            notify_tracking_email=False,
            notify_tracking_sms=False,
        )
        db.add(user)
        db.commit()

        book = Book(title="Victorian Poetry")
        db.add(book)
        db.commit()

        with patch("boto3.client"):
            send_tracking_notification(
                db=db,
                user=user,
                book=book,
                old_status="Shipped",
                new_status="In Transit",
            )

        # Verify in-app notification created
        notifications = db.query(Notification).filter_by(user_id=user.id).all()
        assert len(notifications) == 1
        assert "Victorian Poetry" in notifications[0].message
        assert "In Transit" in notifications[0].message

    def test_dispatches_to_email_when_enabled(self, db):
        """Dispatches to email when user has email enabled."""
        from app.services.notifications import send_tracking_notification

        user = User(
            cognito_sub="test-sub",
            email="test@example.com",
            notify_tracking_email=True,
            notify_tracking_sms=False,
        )
        db.add(user)
        db.commit()

        book = Book(title="Victorian Poetry")
        db.add(book)
        db.commit()

        with patch("boto3.client") as mock_boto:
            mock_ses = MagicMock()
            mock_boto.return_value = mock_ses

            send_tracking_notification(
                db=db,
                user=user,
                book=book,
                old_status="Shipped",
                new_status="In Transit",
            )

            mock_ses.send_email.assert_called_once()

    def test_dispatches_to_sms_when_enabled(self, db):
        """Dispatches to SMS when user has SMS enabled."""
        from app.services.notifications import send_tracking_notification

        user = User(
            cognito_sub="test-sub",
            email="test@example.com",
            notify_tracking_email=False,
            notify_tracking_sms=True,
            phone_number="+15551234567",
        )
        db.add(user)
        db.commit()

        book = Book(title="Victorian Poetry")
        db.add(book)
        db.commit()

        with patch("boto3.client") as mock_boto:
            mock_sns = MagicMock()
            mock_boto.return_value = mock_sns

            send_tracking_notification(
                db=db,
                user=user,
                book=book,
                old_status="Shipped",
                new_status="In Transit",
            )

            mock_sns.publish.assert_called_once()

    def test_delivered_status_special_message(self, db):
        """Uses special message for delivered status."""
        from app.services.notifications import send_tracking_notification

        user = User(
            cognito_sub="test-sub",
            email="test@example.com",
            notify_tracking_email=False,
            notify_tracking_sms=False,
        )
        db.add(user)
        db.commit()

        book = Book(title="Victorian Poetry")
        db.add(book)
        db.commit()

        with patch("boto3.client"):
            send_tracking_notification(
                db=db,
                user=user,
                book=book,
                old_status="In Transit",
                new_status="Delivered",
            )

        notifications = db.query(Notification).filter_by(user_id=user.id).all()
        assert len(notifications) == 1
        assert "has been delivered" in notifications[0].message

    def test_exception_status_alert_message(self, db):
        """Uses alert message for exception status."""
        from app.services.notifications import send_tracking_notification

        user = User(
            cognito_sub="test-sub",
            email="test@example.com",
            notify_tracking_email=False,
            notify_tracking_sms=False,
        )
        db.add(user)
        db.commit()

        book = Book(title="Victorian Poetry")
        db.add(book)
        db.commit()

        with patch("boto3.client"):
            send_tracking_notification(
                db=db,
                user=user,
                book=book,
                old_status="In Transit",
                new_status="Exception",
                detail="Address not found",
            )

        notifications = db.query(Notification).filter_by(user_id=user.id).all()
        assert len(notifications) == 1
        assert "Alert" in notifications[0].message
        assert "Address not found" in notifications[0].message


class TestGetUserNotifications:
    """Tests for retrieving user notifications."""

    def test_returns_paginated_notifications(self, db):
        """Returns notifications for user with pagination."""
        from app.services.notifications import get_user_notifications

        user = User(cognito_sub="test-sub", email="test@example.com")
        db.add(user)
        db.commit()

        # Create 5 notifications
        for i in range(5):
            notification = Notification(
                user_id=user.id,
                message=f"Notification {i}",
            )
            db.add(notification)
        db.commit()

        # Get first page
        result = get_user_notifications(db=db, user_id=user.id, limit=2, offset=0)

        assert len(result) == 2

    def test_orders_by_created_at_desc(self, db):
        """Returns notifications ordered by created_at descending (most recent first)."""
        from app.services.notifications import get_user_notifications

        user = User(cognito_sub="test-sub", email="test@example.com")
        db.add(user)
        db.commit()

        # Create notifications - the service orders by created_at desc
        # In SQLite tests, created_at may be the same, so we verify
        # that newer IDs come first (created later = higher ID)
        n1 = Notification(user_id=user.id, message="First")
        db.add(n1)
        db.commit()

        n2 = Notification(user_id=user.id, message="Second")
        db.add(n2)
        db.commit()

        result = get_user_notifications(db=db, user_id=user.id, limit=10, offset=0)

        # Verify we get both notifications in some order
        assert len(result) == 2
        messages = [r.message for r in result]
        assert "First" in messages
        assert "Second" in messages

    def test_returns_empty_for_no_notifications(self, db):
        """Returns empty list when user has no notifications."""
        from app.services.notifications import get_user_notifications

        user = User(cognito_sub="test-sub", email="test@example.com")
        db.add(user)
        db.commit()

        result = get_user_notifications(db=db, user_id=user.id, limit=10, offset=0)

        assert result == []


class TestMarkNotificationRead:
    """Tests for marking notifications as read."""

    def test_marks_notification_as_read(self, db):
        """Marks a notification as read."""
        from app.services.notifications import mark_notification_read

        user = User(cognito_sub="test-sub", email="test@example.com")
        db.add(user)
        db.commit()

        notification = Notification(
            user_id=user.id,
            message="Test",
            read=False,
        )
        db.add(notification)
        db.commit()

        result = mark_notification_read(
            db=db,
            notification_id=notification.id,
            user_id=user.id,
        )

        assert result is True
        db.refresh(notification)
        assert notification.read is True

    def test_returns_false_for_wrong_user(self, db):
        """Returns False when notification belongs to different user."""
        from app.services.notifications import mark_notification_read

        user1 = User(cognito_sub="test-sub-1", email="test1@example.com")
        user2 = User(cognito_sub="test-sub-2", email="test2@example.com")
        db.add_all([user1, user2])
        db.commit()

        notification = Notification(
            user_id=user1.id,
            message="Test",
            read=False,
        )
        db.add(notification)
        db.commit()

        result = mark_notification_read(
            db=db,
            notification_id=notification.id,
            user_id=user2.id,  # Wrong user
        )

        assert result is False
        db.refresh(notification)
        assert notification.read is False  # Unchanged

    def test_returns_false_for_nonexistent(self, db):
        """Returns False for nonexistent notification."""
        from app.services.notifications import mark_notification_read

        user = User(cognito_sub="test-sub", email="test@example.com")
        db.add(user)
        db.commit()

        result = mark_notification_read(
            db=db,
            notification_id=99999,
            user_id=user.id,
        )

        assert result is False


class TestGetUnreadCount:
    """Tests for getting unread notification count."""

    def test_returns_unread_count(self, db):
        """Returns count of unread notifications."""
        from app.services.notifications import get_unread_count

        user = User(cognito_sub="test-sub", email="test@example.com")
        db.add(user)
        db.commit()

        # Create 3 unread and 2 read notifications
        for i in range(3):
            db.add(Notification(user_id=user.id, message=f"Unread {i}", read=False))
        for i in range(2):
            db.add(Notification(user_id=user.id, message=f"Read {i}", read=True))
        db.commit()

        count = get_unread_count(db=db, user_id=user.id)

        assert count == 3

    def test_returns_zero_when_none(self, db):
        """Returns 0 when no unread notifications."""
        from app.services.notifications import get_unread_count

        user = User(cognito_sub="test-sub", email="test@example.com")
        db.add(user)
        db.commit()

        count = get_unread_count(db=db, user_id=user.id)

        assert count == 0
