"""Tests for notifications router."""

from fastapi.testclient import TestClient

from app.auth import CurrentUser, get_current_user
from app.db import get_db
from app.main import app
from app.models.notification import Notification
from app.models.user import User


class TestGetNotifications:
    """Tests for GET /users/me/notifications endpoint."""

    def test_returns_user_notifications(self, db):
        """Returns notifications for authenticated user."""
        # Create user with notifications
        user = User(cognito_sub="test-sub", email="test@example.com")
        db.add(user)
        db.commit()

        for i in range(3):
            notification = Notification(
                user_id=user.id,
                message=f"Notification {i}",
            )
            db.add(notification)
        db.commit()

        # Mock auth to return this user
        def override_get_current_user():
            return CurrentUser(
                cognito_sub="test-sub",
                email="test@example.com",
                role="viewer",
                db_user=user,
            )

        def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_db] = override_get_db

        try:
            with TestClient(app) as client:
                response = client.get("/api/v1/users/me/notifications")
                assert response.status_code == 200
                data = response.json()
                assert "items" in data
                assert len(data["items"]) == 3
        finally:
            app.dependency_overrides.clear()

    def test_supports_pagination(self, db):
        """Supports limit and offset for pagination."""
        user = User(cognito_sub="test-sub", email="test@example.com")
        db.add(user)
        db.commit()

        for i in range(5):
            notification = Notification(
                user_id=user.id,
                message=f"Notification {i}",
            )
            db.add(notification)
        db.commit()

        def override_get_current_user():
            return CurrentUser(
                cognito_sub="test-sub",
                email="test@example.com",
                role="viewer",
                db_user=user,
            )

        def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_db] = override_get_db

        try:
            with TestClient(app) as client:
                response = client.get("/api/v1/users/me/notifications?limit=2&offset=0")
                assert response.status_code == 200
                data = response.json()
                assert len(data["items"]) == 2
        finally:
            app.dependency_overrides.clear()

    def test_includes_unread_count(self, db):
        """Response includes total unread count."""
        user = User(cognito_sub="test-sub", email="test@example.com")
        db.add(user)
        db.commit()

        # 2 unread, 1 read
        db.add(Notification(user_id=user.id, message="Unread 1", read=False))
        db.add(Notification(user_id=user.id, message="Unread 2", read=False))
        db.add(Notification(user_id=user.id, message="Read 1", read=True))
        db.commit()

        def override_get_current_user():
            return CurrentUser(
                cognito_sub="test-sub",
                email="test@example.com",
                role="viewer",
                db_user=user,
            )

        def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_db] = override_get_db

        try:
            with TestClient(app) as client:
                response = client.get("/api/v1/users/me/notifications")
                assert response.status_code == 200
                data = response.json()
                assert data["unread_count"] == 2
        finally:
            app.dependency_overrides.clear()

    def test_requires_authentication(self, db):
        """Returns 401 when not authenticated."""

        def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        # Don't override get_current_user - will require auth
        app.dependency_overrides.pop(get_current_user, None)

        try:
            with TestClient(app) as client:
                response = client.get("/api/v1/users/me/notifications")
                assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()


class TestMarkNotificationRead:
    """Tests for PATCH /users/me/notifications/{id} endpoint."""

    def test_marks_notification_as_read(self, db):
        """Marks notification as read."""
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

        def override_get_current_user():
            return CurrentUser(
                cognito_sub="test-sub",
                email="test@example.com",
                role="viewer",
                db_user=user,
            )

        def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_db] = override_get_db

        try:
            with TestClient(app) as client:
                response = client.patch(
                    f"/api/v1/users/me/notifications/{notification.id}",
                    json={"read": True},
                )
                assert response.status_code == 200
                data = response.json()
                assert data["read"] is True
        finally:
            app.dependency_overrides.clear()

    def test_returns_404_for_wrong_user(self, db):
        """Returns 404 when notification belongs to different user."""
        user1 = User(cognito_sub="test-sub-1", email="test1@example.com")
        user2 = User(cognito_sub="test-sub-2", email="test2@example.com")
        db.add_all([user1, user2])
        db.commit()

        # Notification belongs to user1
        notification = Notification(
            user_id=user1.id,
            message="Test",
            read=False,
        )
        db.add(notification)
        db.commit()

        # Authenticate as user2
        def override_get_current_user():
            return CurrentUser(
                cognito_sub="test-sub-2",
                email="test2@example.com",
                role="viewer",
                db_user=user2,
            )

        def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_db] = override_get_db

        try:
            with TestClient(app) as client:
                response = client.patch(
                    f"/api/v1/users/me/notifications/{notification.id}",
                    json={"read": True},
                )
                assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    def test_returns_404_for_nonexistent(self, db):
        """Returns 404 for nonexistent notification."""
        user = User(cognito_sub="test-sub", email="test@example.com")
        db.add(user)
        db.commit()

        def override_get_current_user():
            return CurrentUser(
                cognito_sub="test-sub",
                email="test@example.com",
                role="viewer",
                db_user=user,
            )

        def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_db] = override_get_db

        try:
            with TestClient(app) as client:
                response = client.patch(
                    "/api/v1/users/me/notifications/99999",
                    json={"read": True},
                )
                assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


class TestUpdatePreferences:
    """Tests for PATCH /users/me/preferences endpoint."""

    def test_updates_notification_preferences(self, db):
        """Updates user notification preferences."""
        user = User(
            cognito_sub="test-sub",
            email="test@example.com",
            notify_tracking_email=True,
            notify_tracking_sms=False,
        )
        db.add(user)
        db.commit()

        def override_get_current_user():
            return CurrentUser(
                cognito_sub="test-sub",
                email="test@example.com",
                role="viewer",
                db_user=user,
            )

        def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_db] = override_get_db

        try:
            with TestClient(app) as client:
                response = client.patch(
                    "/api/v1/users/me/preferences",
                    json={
                        "notify_tracking_email": False,
                        "notify_tracking_sms": True,
                        "phone_number": "+15551234567",
                    },
                )
                assert response.status_code == 200
                data = response.json()
                assert data["notify_tracking_email"] is False
                assert data["notify_tracking_sms"] is True
                assert data["phone_number"] == "+15551234567"
        finally:
            app.dependency_overrides.clear()

    def test_partial_update(self, db):
        """Can update only some preferences."""
        user = User(
            cognito_sub="test-sub",
            email="test@example.com",
            notify_tracking_email=True,
            notify_tracking_sms=False,
        )
        db.add(user)
        db.commit()

        def override_get_current_user():
            return CurrentUser(
                cognito_sub="test-sub",
                email="test@example.com",
                role="viewer",
                db_user=user,
            )

        def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_db] = override_get_db

        try:
            with TestClient(app) as client:
                response = client.patch(
                    "/api/v1/users/me/preferences",
                    json={"notify_tracking_email": False},
                )
                assert response.status_code == 200
                data = response.json()
                assert data["notify_tracking_email"] is False
                # Unchanged
                assert data["notify_tracking_sms"] is False
        finally:
            app.dependency_overrides.clear()

    def test_returns_404_when_no_db_user(self, db):
        """Returns 404 when user not in database."""

        def override_get_current_user():
            return CurrentUser(
                cognito_sub="test-sub",
                email="test@example.com",
                role="viewer",
                db_user=None,  # No DB user
            )

        def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_db] = override_get_db

        try:
            with TestClient(app) as client:
                response = client.patch(
                    "/api/v1/users/me/preferences",
                    json={"notify_tracking_email": False},
                )
                assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()
