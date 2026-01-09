"""Integration tests for edition auto-inference in book create/update.

Tests that is_first_edition is automatically inferred from edition text
when creating or updating books.
"""


class TestEditionAutoInferOnCreate:
    """Tests for auto-inferring is_first_edition on book creation."""

    def test_create_book_first_edition_infers_true(self, client):
        """Creating a book with 'First Edition' sets is_first_edition=True."""
        response = client.post(
            "/api/v1/books",
            json={
                "title": "Test Book",
                "edition": "First Edition",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["is_first_edition"] is True

    def test_create_book_1st_ed_infers_true(self, client):
        """Creating a book with '1st ed.' sets is_first_edition=True."""
        response = client.post(
            "/api/v1/books",
            json={
                "title": "Test Book",
                "edition": "1st ed.",
            },
        )
        assert response.status_code == 201
        assert response.json()["is_first_edition"] is True

    def test_create_book_second_edition_infers_false(self, client):
        """Creating a book with 'Second Edition' sets is_first_edition=False."""
        response = client.post(
            "/api/v1/books",
            json={
                "title": "Test Book",
                "edition": "Second Edition",
            },
        )
        assert response.status_code == 201
        assert response.json()["is_first_edition"] is False

    def test_create_book_no_edition_leaves_null(self, client):
        """Creating a book without edition leaves is_first_edition as null."""
        response = client.post(
            "/api/v1/books",
            json={
                "title": "Test Book",
            },
        )
        assert response.status_code == 201
        assert response.json()["is_first_edition"] is None

    def test_create_book_explicit_is_first_edition_not_overwritten(self, client):
        """Explicit is_first_edition value should NOT be overwritten."""
        response = client.post(
            "/api/v1/books",
            json={
                "title": "Test Book",
                "edition": "First Edition",  # Would infer True
                "is_first_edition": False,  # Explicitly set to False
            },
        )
        assert response.status_code == 201
        # Explicit value should be preserved
        assert response.json()["is_first_edition"] is False

    def test_create_book_explicit_null_allows_inference(self, client):
        """Explicit null for is_first_edition should allow inference."""
        response = client.post(
            "/api/v1/books",
            json={
                "title": "Test Book",
                "edition": "First Edition",
                "is_first_edition": None,
            },
        )
        assert response.status_code == 201
        assert response.json()["is_first_edition"] is True


class TestEditionAutoInferOnUpdate:
    """Tests for auto-inferring is_first_edition on book update."""

    def test_update_edition_to_first_infers_true(self, client):
        """Updating edition to 'First Edition' sets is_first_edition=True."""
        # Create book without edition
        create_response = client.post(
            "/api/v1/books",
            json={"title": "Test Book"},
        )
        book_id = create_response.json()["id"]

        # Update with edition
        response = client.put(
            f"/api/v1/books/{book_id}",
            json={"edition": "First Edition"},
        )
        assert response.status_code == 200
        assert response.json()["is_first_edition"] is True

    def test_update_edition_to_second_infers_false(self, client):
        """Updating edition to 'Second Edition' sets is_first_edition=False."""
        # Create book without edition
        create_response = client.post(
            "/api/v1/books",
            json={"title": "Test Book"},
        )
        book_id = create_response.json()["id"]

        # Update with edition
        response = client.put(
            f"/api/v1/books/{book_id}",
            json={"edition": "Second Edition"},
        )
        assert response.status_code == 200
        assert response.json()["is_first_edition"] is False

    def test_update_edition_does_not_override_explicit(self, client):
        """Updating edition should not override explicit is_first_edition."""
        # Create book with explicit is_first_edition=False
        create_response = client.post(
            "/api/v1/books",
            json={
                "title": "Test Book",
                "is_first_edition": False,
            },
        )
        book_id = create_response.json()["id"]

        # Update edition to 'First Edition' - should NOT change is_first_edition
        response = client.put(
            f"/api/v1/books/{book_id}",
            json={"edition": "First Edition"},
        )
        assert response.status_code == 200
        # Explicit False should be preserved
        assert response.json()["is_first_edition"] is False

    def test_update_other_field_does_not_reinfer(self, client):
        """Updating non-edition field should not trigger re-inference."""
        # Create book with edition but is_first_edition manually set differently
        create_response = client.post(
            "/api/v1/books",
            json={
                "title": "Test Book",
                "edition": "First Edition",
            },
        )
        book_id = create_response.json()["id"]

        # Manually set to False via update (simulate user override)
        client.put(
            f"/api/v1/books/{book_id}",
            json={"is_first_edition": False},
        )

        # Update title - should not re-infer from edition
        response = client.put(
            f"/api/v1/books/{book_id}",
            json={"title": "Updated Title"},
        )
        assert response.status_code == 200
        assert response.json()["is_first_edition"] is False

    def test_update_edition_does_not_change_already_set_value(self, client):
        """Changing edition should NOT change already-set is_first_edition.

        Once is_first_edition has a value (True or False), updating the edition
        text should not change it. This prevents accidental data loss if user
        has verified the first edition status independently.
        """
        # Create book with First Edition - is_first_edition auto-inferred to True
        create_response = client.post(
            "/api/v1/books",
            json={
                "title": "Test Book",
                "edition": "First Edition",
            },
        )
        book_id = create_response.json()["id"]
        assert create_response.json()["is_first_edition"] is True

        # Change edition to Second Edition - is_first_edition should NOT change
        # because it was already set (to True) during create
        response = client.put(
            f"/api/v1/books/{book_id}",
            json={"edition": "Second Edition"},
        )
        assert response.status_code == 200
        # Value is preserved - user/system already made a determination
        assert response.json()["is_first_edition"] is True
