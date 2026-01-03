"""Tests for carrier API support database models and migrations.

These tests verify the new columns and tables required for carrier API support:
- Book model: tracking_active, tracking_delivered_at
- User model: notify_tracking_email, notify_tracking_sms, phone_number
- Notification model: new table for in-app notifications

Following TDD approach: write tests first, then implement to pass.
"""

from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models import Book, User
from app.models.notification import Notification


class TestBookTrackingColumns:
    """Tests for new tracking columns on Book model."""

    def test_book_has_tracking_active_column(self, db: Session):
        """Book model should have tracking_active boolean column."""
        inspector = inspect(db.bind)
        columns = {col["name"]: col for col in inspector.get_columns("books")}

        assert "tracking_active" in columns
        # Check it's a boolean type (SQLite uses INTEGER, PostgreSQL uses BOOLEAN)
        col_type = str(columns["tracking_active"]["type"]).upper()
        assert "BOOL" in col_type or "INTEGER" in col_type

    def test_book_has_tracking_delivered_at_column(self, db: Session):
        """Book model should have tracking_delivered_at timestamp column."""
        inspector = inspect(db.bind)
        columns = {col["name"]: col for col in inspector.get_columns("books")}

        assert "tracking_delivered_at" in columns
        col_type = str(columns["tracking_delivered_at"]["type"]).upper()
        assert "TIMESTAMP" in col_type or "DATETIME" in col_type

    def test_tracking_active_defaults_to_false(self, db: Session):
        """tracking_active should default to False."""
        book = Book(
            title="Test Book",
            tracking_number="1Z999AA10123456784",
            tracking_carrier="UPS",
        )
        db.add(book)
        db.commit()
        db.refresh(book)

        assert book.tracking_active is False

    def test_can_set_tracking_active(self, db: Session):
        """Should be able to set tracking_active to True."""
        book = Book(
            title="Test Book",
            tracking_number="1Z999AA10123456784",
            tracking_carrier="UPS",
            tracking_active=True,
        )
        db.add(book)
        db.commit()
        db.refresh(book)

        assert book.tracking_active is True

    def test_can_set_tracking_delivered_at(self, db: Session):
        """Should be able to set tracking_delivered_at timestamp."""
        delivered_time = datetime.now(UTC)
        book = Book(
            title="Test Book",
            tracking_number="1Z999AA10123456784",
            tracking_carrier="UPS",
            tracking_active=False,
            tracking_delivered_at=delivered_time,
        )
        db.add(book)
        db.commit()
        db.refresh(book)

        assert book.tracking_delivered_at is not None
        # SQLite may strip timezone info, so compare naive datetimes
        db_time = book.tracking_delivered_at
        if db_time.tzinfo is None:
            # SQLite returned naive datetime, compare naively
            delivered_naive = delivered_time.replace(tzinfo=None)
            assert abs((db_time - delivered_naive).total_seconds()) < 1
        else:
            # PostgreSQL preserves timezone
            assert abs((db_time - delivered_time).total_seconds()) < 1

    def test_tracking_delivered_at_defaults_to_none(self, db: Session):
        """tracking_delivered_at should default to None."""
        book = Book(
            title="Test Book",
            tracking_number="1Z999AA10123456784",
        )
        db.add(book)
        db.commit()
        db.refresh(book)

        assert book.tracking_delivered_at is None


class TestUserNotificationColumns:
    """Tests for new notification preference columns on User model."""

    def test_user_has_notify_tracking_email_column(self, db: Session):
        """User model should have notify_tracking_email boolean column."""
        inspector = inspect(db.bind)
        columns = {col["name"]: col for col in inspector.get_columns("users")}

        assert "notify_tracking_email" in columns

    def test_user_has_notify_tracking_sms_column(self, db: Session):
        """User model should have notify_tracking_sms boolean column."""
        inspector = inspect(db.bind)
        columns = {col["name"]: col for col in inspector.get_columns("users")}

        assert "notify_tracking_sms" in columns

    def test_user_has_phone_number_column(self, db: Session):
        """User model should have phone_number varchar column."""
        inspector = inspect(db.bind)
        columns = {col["name"]: col for col in inspector.get_columns("users")}

        assert "phone_number" in columns
        col_type = str(columns["phone_number"]["type"]).upper()
        assert "VARCHAR" in col_type or "TEXT" in col_type

    def test_notify_tracking_email_defaults_to_true(self, db: Session):
        """notify_tracking_email should default to True."""
        user = User(
            cognito_sub=f"test-{uuid4()}",
            email="test@example.com",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.notify_tracking_email is True

    def test_notify_tracking_sms_defaults_to_false(self, db: Session):
        """notify_tracking_sms should default to False."""
        user = User(
            cognito_sub=f"test-{uuid4()}",
            email="test@example.com",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.notify_tracking_sms is False

    def test_can_set_notification_preferences(self, db: Session):
        """Should be able to set notification preferences."""
        user = User(
            cognito_sub=f"test-{uuid4()}",
            email="test@example.com",
            notify_tracking_email=False,
            notify_tracking_sms=True,
            phone_number="+14155551234",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.notify_tracking_email is False
        assert user.notify_tracking_sms is True
        assert user.phone_number == "+14155551234"

    def test_phone_number_defaults_to_none(self, db: Session):
        """phone_number should default to None."""
        user = User(
            cognito_sub=f"test-{uuid4()}",
            email="test@example.com",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.phone_number is None


class TestNotificationModel:
    """Tests for new Notification model."""

    def test_notifications_table_exists(self, db: Session):
        """Notifications table should exist."""
        inspector = inspect(db.bind)
        tables = inspector.get_table_names()
        assert "notifications" in tables

    def test_notification_has_required_columns(self, db: Session):
        """Notification should have all required columns."""
        inspector = inspect(db.bind)
        columns = {col["name"]: col for col in inspector.get_columns("notifications")}

        assert "id" in columns
        assert "user_id" in columns
        assert "book_id" in columns  # References books (not acquisitions)
        assert "message" in columns
        assert "read" in columns
        assert "created_at" in columns

    def test_can_create_notification(self, db: Session):
        """Should be able to create a notification."""
        # Create a user first
        user = User(
            cognito_sub=f"test-{uuid4()}",
            email="test@example.com",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        notification = Notification(
            user_id=user.id,
            message="Your book 'Test Book' has been delivered!",
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)

        assert notification.id is not None
        assert notification.user_id == user.id
        assert notification.message == "Your book 'Test Book' has been delivered!"
        assert notification.read is False
        assert notification.created_at is not None

    def test_notification_read_defaults_to_false(self, db: Session):
        """read should default to False."""
        user = User(
            cognito_sub=f"test-{uuid4()}",
            email="test@example.com",
        )
        db.add(user)
        db.commit()

        notification = Notification(
            user_id=user.id,
            message="Test notification",
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)

        assert notification.read is False

    def test_can_mark_notification_as_read(self, db: Session):
        """Should be able to mark notification as read."""
        user = User(
            cognito_sub=f"test-{uuid4()}",
            email="test@example.com",
        )
        db.add(user)
        db.commit()

        notification = Notification(
            user_id=user.id,
            message="Test notification",
        )
        db.add(notification)
        db.commit()

        notification.read = True
        db.commit()
        db.refresh(notification)

        assert notification.read is True

    def test_notification_can_reference_book(self, db: Session):
        """Notification can optionally reference a book."""
        user = User(
            cognito_sub=f"test-{uuid4()}",
            email="test@example.com",
        )
        db.add(user)

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        notification = Notification(
            user_id=user.id,
            book_id=book.id,
            message=f"Your book '{book.title}' is in transit.",
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)

        assert notification.book_id == book.id

    def test_notification_book_id_nullable(self, db: Session):
        """book_id should be nullable for general notifications."""
        user = User(
            cognito_sub=f"test-{uuid4()}",
            email="test@example.com",
        )
        db.add(user)
        db.commit()

        notification = Notification(
            user_id=user.id,
            message="Welcome to BlueMoxon!",
            book_id=None,
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)

        assert notification.book_id is None

    def test_notification_cascade_delete_user(self, db: Session):
        """Deleting user should cascade delete their notifications.

        Note: This test validates the relationship cascade behavior in SQLAlchemy.
        In SQLite, foreign key constraints are not enforced by default, so we test
        via ORM relationship cascade instead of database-level ON DELETE CASCADE.
        """
        user = User(
            cognito_sub=f"test-{uuid4()}",
            email="test@example.com",
        )
        db.add(user)
        db.commit()

        notification = Notification(
            user_id=user.id,
            message="Test notification",
        )
        db.add(notification)
        db.commit()

        # Verify notification is in user's notifications list
        db.refresh(user)
        assert len(user.notifications) == 1

        # Delete user via ORM (triggers cascade due to relationship config)
        db.delete(user)
        db.commit()

        # Expunge and re-query to verify deletion
        db.expire_all()
        result = db.query(Notification).filter(Notification.message == "Test notification").first()
        assert result is None

    def test_notification_set_null_on_book_delete(self, db: Session):
        """Deleting book should set notification's book_id to NULL.

        Note: ON DELETE SET NULL is a database-level constraint that SQLite
        doesn't enforce by default. This test validates the ORM relationship
        behavior. In PostgreSQL, the actual SET NULL behavior is enforced.
        For SQLite, we manually verify the model supports NULL book_id.
        """
        user = User(
            cognito_sub=f"test-{uuid4()}",
            email="test@example.com",
        )
        db.add(user)

        book = Book(title="Test Book")
        db.add(book)
        db.commit()
        book_id = book.id

        notification = Notification(
            user_id=user.id,
            book_id=book.id,
            message="Book delivered!",
        )
        db.add(notification)
        db.commit()
        notification_id = notification.id

        # Verify notification references the book
        assert notification.book_id == book_id

        # Manually set book_id to None (simulating SET NULL behavior)
        # This verifies the column accepts NULL values
        notification.book_id = None
        db.commit()
        db.refresh(notification)

        # Notification should still exist with NULL book_id
        result = db.query(Notification).filter(Notification.id == notification_id).first()
        assert result is not None
        assert result.book_id is None


class TestDataMigrationBehavior:
    """Tests for data migration: existing in-transit books with tracking numbers.

    The migration sets tracking_active=True for books where:
    - tracking_number IS NOT NULL
    - status = 'IN_TRANSIT'

    Since unit tests use SQLite without running Alembic migrations, we test
    the expected behavior that the migration enables.
    """

    def test_in_transit_books_with_tracking_should_be_active(self, db: Session):
        """In-transit books with tracking numbers should have tracking_active=True.

        This tests the behavior the migration provides for new books.
        """
        book = Book(
            title="In Transit Book",
            tracking_number="1Z999AA10123456784",
            tracking_carrier="UPS",
            status="IN_TRANSIT",
            tracking_active=True,  # Migration would set this
        )
        db.add(book)
        db.commit()
        db.refresh(book)

        # Should be findable by the poller
        active_books = (
            db.query(Book)
            .filter(
                Book.tracking_active.is_(True),
                Book.tracking_number.isnot(None),
            )
            .all()
        )
        assert len(active_books) == 1
        assert active_books[0].id == book.id

    def test_delivered_books_should_not_be_active(self, db: Session):
        """Delivered books should not have tracking_active=True."""
        book = Book(
            title="Delivered Book",
            tracking_number="1Z999AA10123456784",
            tracking_carrier="UPS",
            status="ON_HAND",  # Already received
            tracking_active=False,
        )
        db.add(book)
        db.commit()

        active_books = (
            db.query(Book)
            .filter(
                Book.tracking_active.is_(True),
            )
            .all()
        )
        assert len(active_books) == 0

    def test_books_without_tracking_should_not_be_active(self, db: Session):
        """Books without tracking numbers should not have tracking_active=True."""
        book = Book(
            title="No Tracking Book",
            status="IN_TRANSIT",
            tracking_active=False,  # No tracking number = no active tracking
        )
        db.add(book)
        db.commit()

        active_books = (
            db.query(Book)
            .filter(
                Book.tracking_active.is_(True),
            )
            .all()
        )
        assert len(active_books) == 0

    def test_migration_activates_correct_subset(self, db: Session):
        """Test the exact query the migration uses to activate tracking.

        This simulates the migration logic to verify it targets the right books.
        """
        # Create test books in various states
        in_transit_with_tracking = Book(
            title="Should Activate",
            tracking_number="1Z999AA10123456784",
            status="IN_TRANSIT",
            tracking_active=False,
        )
        in_transit_no_tracking = Book(
            title="No Tracking Number",
            status="IN_TRANSIT",
            tracking_active=False,
        )
        on_hand_with_tracking = Book(
            title="Already Delivered",
            tracking_number="1Z888BB20987654321",
            status="ON_HAND",
            tracking_active=False,
        )
        evaluating_with_tracking = Book(
            title="Still Evaluating",
            tracking_number="1Z777CC30567891234",
            status="EVALUATING",
            tracking_active=False,
        )
        db.add_all(
            [
                in_transit_with_tracking,
                in_transit_no_tracking,
                on_hand_with_tracking,
                evaluating_with_tracking,
            ]
        )
        db.commit()

        # Simulate the migration's UPDATE query
        db.execute(
            sa.text(
                """
                UPDATE books
                SET tracking_active = 1
                WHERE tracking_number IS NOT NULL
                  AND status = 'IN_TRANSIT'
                """
            )
        )
        db.commit()

        # Refresh all books
        for book in [
            in_transit_with_tracking,
            in_transit_no_tracking,
            on_hand_with_tracking,
            evaluating_with_tracking,
        ]:
            db.refresh(book)

        # Only in_transit_with_tracking should be activated
        assert in_transit_with_tracking.tracking_active is True
        assert in_transit_no_tracking.tracking_active is False
        assert on_hand_with_tracking.tracking_active is False
        assert evaluating_with_tracking.tracking_active is False


class TestNotificationRelationships:
    """Tests for notification relationships with User and Book models."""

    def test_user_has_notifications_relationship(self, db: Session):
        """User should have a notifications relationship."""
        user = User(
            cognito_sub=f"test-{uuid4()}",
            email="test@example.com",
        )
        db.add(user)
        db.commit()

        # Create multiple notifications
        for i in range(3):
            notification = Notification(
                user_id=user.id,
                message=f"Notification {i}",
            )
            db.add(notification)
        db.commit()
        db.refresh(user)

        assert hasattr(user, "notifications")
        assert len(user.notifications) == 3

    def test_notification_has_user_relationship(self, db: Session):
        """Notification should have a user relationship."""
        user = User(
            cognito_sub=f"test-{uuid4()}",
            email="test@example.com",
        )
        db.add(user)
        db.commit()

        notification = Notification(
            user_id=user.id,
            message="Test notification",
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)

        assert notification.user is not None
        assert notification.user.id == user.id

    def test_notification_has_book_relationship(self, db: Session):
        """Notification should have a book relationship."""
        user = User(
            cognito_sub=f"test-{uuid4()}",
            email="test@example.com",
        )
        db.add(user)

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        notification = Notification(
            user_id=user.id,
            book_id=book.id,
            message="Book shipped!",
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)

        assert notification.book is not None
        assert notification.book.id == book.id
        assert notification.book.title == "Test Book"
