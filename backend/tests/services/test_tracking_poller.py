"""Tests for tracking poller service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.models import Book, Notification, User
from app.services.carriers.base import TrackingResult


class TestPollAllActiveTracking:
    """Tests for poll_all_active_tracking function."""

    def test_returns_stats_dict(self, db):
        """Should return a dict with stats keys."""
        from app.services.tracking_poller import poll_all_active_tracking

        result = poll_all_active_tracking(db)

        assert isinstance(result, dict)
        assert "checked" in result
        assert "changed" in result
        assert "errors" in result
        assert "deactivated" in result

    def test_no_active_tracking_returns_zeros(self, db):
        """With no active tracking, all stats should be zero."""
        from app.services.tracking_poller import poll_all_active_tracking

        # Create a book without active tracking
        book = Book(
            title="Test Book",
            tracking_number="1Z999AA10123456784",
            tracking_carrier="UPS",
            tracking_active=False,
        )
        db.add(book)
        db.commit()

        result = poll_all_active_tracking(db)

        assert result["checked"] == 0
        assert result["changed"] == 0
        assert result["errors"] == 0
        assert result["deactivated"] == 0

    def test_only_polls_active_tracking(self, db):
        """Should only poll books where tracking_active is True."""
        from app.services.tracking_poller import poll_all_active_tracking

        # Create inactive tracking
        inactive_book = Book(
            title="Inactive",
            tracking_number="1Z999AA10123456784",
            tracking_carrier="UPS",
            tracking_active=False,
        )
        # Create active tracking
        active_book = Book(
            title="Active",
            tracking_number="1Z888BB10123456784",
            tracking_carrier="UPS",
            tracking_active=True,
        )
        db.add_all([inactive_book, active_book])
        db.commit()

        with patch("app.services.tracking_poller.get_carrier") as mock_get_carrier:
            mock_carrier = MagicMock()
            mock_carrier.fetch_tracking.return_value = TrackingResult(status="In Transit")
            mock_get_carrier.return_value = mock_carrier

            result = poll_all_active_tracking(db)

            # Should only poll the active book
            assert result["checked"] == 1
            mock_get_carrier.assert_called_once_with("UPS")

    def test_skips_books_without_tracking_number(self, db):
        """Should skip books without tracking number even if tracking_active is True."""
        from app.services.tracking_poller import poll_all_active_tracking

        book = Book(
            title="No Tracking Number",
            tracking_number=None,
            tracking_carrier="UPS",
            tracking_active=True,
        )
        db.add(book)
        db.commit()

        result = poll_all_active_tracking(db)

        assert result["checked"] == 0

    @patch("app.services.tracking_poller.get_carrier")
    def test_updates_tracking_status(self, mock_get_carrier, db):
        """Should update tracking_status when carrier returns new status."""
        from app.services.tracking_poller import poll_all_active_tracking

        book = Book(
            title="Test Book",
            tracking_number="1Z999AA10123456784",
            tracking_carrier="UPS",
            tracking_active=True,
            tracking_status="Label Created",
        )
        db.add(book)
        db.commit()

        mock_carrier = MagicMock()
        mock_carrier.fetch_tracking.return_value = TrackingResult(status="In Transit")
        mock_get_carrier.return_value = mock_carrier

        result = poll_all_active_tracking(db)

        db.refresh(book)
        assert book.tracking_status == "In Transit"
        assert result["changed"] == 1

    @patch("app.services.tracking_poller.get_carrier")
    def test_no_change_when_status_same(self, mock_get_carrier, db):
        """Should not count as changed when status is the same."""
        from app.services.tracking_poller import poll_all_active_tracking

        book = Book(
            title="Test Book",
            tracking_number="1Z999AA10123456784",
            tracking_carrier="UPS",
            tracking_active=True,
            tracking_status="In Transit",
        )
        db.add(book)
        db.commit()

        mock_carrier = MagicMock()
        mock_carrier.fetch_tracking.return_value = TrackingResult(status="In Transit")
        mock_get_carrier.return_value = mock_carrier

        result = poll_all_active_tracking(db)

        assert result["changed"] == 0
        assert result["checked"] == 1

    @patch("app.services.tracking_poller.get_carrier")
    def test_updates_tracking_last_checked(self, mock_get_carrier, db):
        """Should update tracking_last_checked timestamp."""
        from app.services.tracking_poller import poll_all_active_tracking

        book = Book(
            title="Test Book",
            tracking_number="1Z999AA10123456784",
            tracking_carrier="UPS",
            tracking_active=True,
            tracking_last_checked=None,
        )
        db.add(book)
        db.commit()

        mock_carrier = MagicMock()
        mock_carrier.fetch_tracking.return_value = TrackingResult(status="In Transit")
        mock_get_carrier.return_value = mock_carrier

        before = datetime.now(UTC)
        poll_all_active_tracking(db)
        after = datetime.now(UTC)

        db.refresh(book)
        assert book.tracking_last_checked is not None
        # Handle timezone-aware/naive comparison
        last_checked = book.tracking_last_checked
        if last_checked.tzinfo is None:
            last_checked = last_checked.replace(tzinfo=UTC)
        assert before <= last_checked <= after

    @patch("app.services.tracking_poller.get_carrier")
    def test_sets_delivered_at_on_delivery(self, mock_get_carrier, db):
        """Should set tracking_delivered_at when status changes to Delivered."""
        from app.services.tracking_poller import poll_all_active_tracking

        book = Book(
            title="Test Book",
            tracking_number="1Z999AA10123456784",
            tracking_carrier="UPS",
            tracking_active=True,
            tracking_status="In Transit",
            tracking_delivered_at=None,
        )
        db.add(book)
        db.commit()

        mock_carrier = MagicMock()
        mock_carrier.fetch_tracking.return_value = TrackingResult(status="Delivered")
        mock_get_carrier.return_value = mock_carrier

        poll_all_active_tracking(db)

        db.refresh(book)
        assert book.tracking_delivered_at is not None
        assert book.tracking_status == "Delivered"

    @patch("app.services.tracking_poller.get_carrier")
    def test_deactivates_7_days_after_delivery(self, mock_get_carrier, db):
        """Should deactivate tracking 7 days after delivery."""
        from app.services.tracking_poller import poll_all_active_tracking

        # Book delivered 8 days ago
        delivered_time = datetime.now(UTC) - timedelta(days=8)
        book = Book(
            title="Test Book",
            tracking_number="1Z999AA10123456784",
            tracking_carrier="UPS",
            tracking_active=True,
            tracking_status="Delivered",
            tracking_delivered_at=delivered_time,
        )
        db.add(book)
        db.commit()

        mock_carrier = MagicMock()
        mock_carrier.fetch_tracking.return_value = TrackingResult(status="Delivered")
        mock_get_carrier.return_value = mock_carrier

        result = poll_all_active_tracking(db)

        db.refresh(book)
        assert book.tracking_active is False
        assert result["deactivated"] == 1

    @patch("app.services.tracking_poller.get_carrier")
    def test_does_not_deactivate_before_7_days(self, mock_get_carrier, db):
        """Should not deactivate tracking before 7 days after delivery."""
        from app.services.tracking_poller import poll_all_active_tracking

        # Book delivered 5 days ago
        delivered_time = datetime.now(UTC) - timedelta(days=5)
        book = Book(
            title="Test Book",
            tracking_number="1Z999AA10123456784",
            tracking_carrier="UPS",
            tracking_active=True,
            tracking_status="Delivered",
            tracking_delivered_at=delivered_time,
        )
        db.add(book)
        db.commit()

        mock_carrier = MagicMock()
        mock_carrier.fetch_tracking.return_value = TrackingResult(status="Delivered")
        mock_get_carrier.return_value = mock_carrier

        result = poll_all_active_tracking(db)

        db.refresh(book)
        assert book.tracking_active is True
        assert result["deactivated"] == 0

    @patch("app.services.tracking_poller.get_carrier")
    def test_counts_errors(self, mock_get_carrier, db):
        """Should count errors when carrier API fails."""
        from app.services.tracking_poller import poll_all_active_tracking

        book = Book(
            title="Test Book",
            tracking_number="1Z999AA10123456784",
            tracking_carrier="UPS",
            tracking_active=True,
        )
        db.add(book)
        db.commit()

        mock_carrier = MagicMock()
        mock_carrier.fetch_tracking.side_effect = Exception("API Error")
        mock_get_carrier.return_value = mock_carrier

        result = poll_all_active_tracking(db)

        assert result["errors"] == 1
        assert result["checked"] == 1

    @patch("app.services.tracking_poller.get_carrier")
    def test_unknown_carrier_counts_as_error(self, mock_get_carrier, db):
        """Should count as error when carrier is unknown."""
        from app.services.tracking_poller import poll_all_active_tracking

        book = Book(
            title="Test Book",
            tracking_number="1234567890",
            tracking_carrier="UnknownCarrier",
            tracking_active=True,
        )
        db.add(book)
        db.commit()

        mock_get_carrier.side_effect = KeyError("Unknown carrier: UnknownCarrier")

        result = poll_all_active_tracking(db)

        assert result["errors"] == 1


class TestNotifyStatusChange:
    """Tests for notify_status_change function."""

    def test_creates_notification(self, db):
        """Should create a notification for the user."""
        from app.services.tracking_poller import notify_status_change

        user = User(cognito_sub="test-user-123", email="test@example.com")
        db.add(user)
        db.commit()

        book = Book(title="Test Book", tracking_number="1Z999AA10123456784")
        db.add(book)
        db.commit()

        notify_status_change(db, user, book, "In Transit", "Out for Delivery")

        notifications = db.query(Notification).filter_by(user_id=user.id).all()
        assert len(notifications) == 1
        assert book.id == notifications[0].book_id
        assert "Test Book" in notifications[0].message
        assert "Out for Delivery" in notifications[0].message

    def test_notification_message_format(self, db):
        """Notification message should include book title and new status."""
        from app.services.tracking_poller import notify_status_change

        user = User(cognito_sub="test-user-456", email="user@example.com")
        db.add(user)
        db.commit()

        book = Book(title="Rare Victorian Edition", tracking_number="ABC123")
        db.add(book)
        db.commit()

        notify_status_change(db, user, book, "Label Created", "Delivered")

        notification = db.query(Notification).filter_by(user_id=user.id).first()
        assert "Rare Victorian Edition" in notification.message
        assert "Delivered" in notification.message

    def test_notification_defaults_to_unread(self, db):
        """Notification should default to unread."""
        from app.services.tracking_poller import notify_status_change

        user = User(cognito_sub="test-user-789", email="reader@example.com")
        db.add(user)
        db.commit()

        book = Book(title="Test Book", tracking_number="XYZ789")
        db.add(book)
        db.commit()

        notify_status_change(db, user, book, "In Transit", "Delivered")

        notification = db.query(Notification).filter_by(user_id=user.id).first()
        assert notification.read is False


class TestRefreshSingleBookTracking:
    """Tests for refresh_single_book_tracking function."""

    @patch("app.services.tracking_poller.get_carrier")
    def test_refreshes_single_book(self, mock_get_carrier, db):
        """Should refresh tracking for a single book."""
        from app.services.tracking_poller import refresh_single_book_tracking

        book = Book(
            title="Test Book",
            tracking_number="1Z999AA10123456784",
            tracking_carrier="UPS",
            tracking_active=True,
            tracking_status="Label Created",
        )
        db.add(book)
        db.commit()

        mock_carrier = MagicMock()
        mock_carrier.fetch_tracking.return_value = TrackingResult(status="In Transit")
        mock_get_carrier.return_value = mock_carrier

        result = refresh_single_book_tracking(db, book.id)

        db.refresh(book)
        assert book.tracking_status == "In Transit"
        assert result["status"] == "In Transit"
        assert result["changed"] is True

    @patch("app.services.tracking_poller.get_carrier")
    def test_refresh_without_tracking_number_raises(self, mock_get_carrier, db):
        """Should raise error if book has no tracking number."""
        from app.services.tracking_poller import refresh_single_book_tracking

        book = Book(
            title="Test Book",
            tracking_number=None,
            tracking_carrier=None,
            tracking_active=False,
        )
        db.add(book)
        db.commit()

        with pytest.raises(ValueError) as exc_info:
            refresh_single_book_tracking(db, book.id)
        assert "No tracking number" in str(exc_info.value)

    def test_refresh_nonexistent_book_raises(self, db):
        """Should raise error if book doesn't exist."""
        from app.services.tracking_poller import refresh_single_book_tracking

        with pytest.raises(ValueError) as exc_info:
            refresh_single_book_tracking(db, 99999)
        assert "Book not found" in str(exc_info.value)

    @patch("app.services.tracking_poller.get_carrier")
    def test_refresh_activates_tracking(self, mock_get_carrier, db):
        """Refreshing should activate tracking if not already active."""
        from app.services.tracking_poller import refresh_single_book_tracking

        book = Book(
            title="Test Book",
            tracking_number="1Z999AA10123456784",
            tracking_carrier="UPS",
            tracking_active=False,
        )
        db.add(book)
        db.commit()

        mock_carrier = MagicMock()
        mock_carrier.fetch_tracking.return_value = TrackingResult(status="In Transit")
        mock_get_carrier.return_value = mock_carrier

        refresh_single_book_tracking(db, book.id)

        db.refresh(book)
        assert book.tracking_active is True

    @patch("app.services.tracking_poller.get_carrier")
    def test_refresh_returns_full_result(self, mock_get_carrier, db):
        """Should return complete result with all tracking info."""
        from app.services.tracking_poller import refresh_single_book_tracking

        book = Book(
            title="Test Book",
            tracking_number="1Z999AA10123456784",
            tracking_carrier="UPS",
            tracking_active=True,
            tracking_status="Label Created",
        )
        db.add(book)
        db.commit()

        mock_carrier = MagicMock()
        mock_carrier.fetch_tracking.return_value = TrackingResult(
            status="In Transit",
            status_detail="Package is on the way",
            location="New York, NY",
        )
        mock_get_carrier.return_value = mock_carrier

        result = refresh_single_book_tracking(db, book.id)

        assert result["status"] == "In Transit"
        assert result["status_detail"] == "Package is on the way"
        assert result["location"] == "New York, NY"
        assert result["changed"] is True
        assert result["previous_status"] == "Label Created"
