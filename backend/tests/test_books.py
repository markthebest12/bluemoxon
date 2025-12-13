"""Book API tests."""


class TestListBooks:
    """Tests for GET /api/v1/books."""

    def test_list_books_empty(self, client):
        """Test listing books when database is empty."""
        response = client.get("/api/v1/books")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1

    def test_list_books_pagination(self, client):
        """Test pagination parameters."""
        response = client.get("/api/v1/books?page=1&per_page=10")
        assert response.status_code == 200
        data = response.json()
        assert data["per_page"] == 10


class TestCreateBook:
    """Tests for POST /api/v1/books."""

    def test_create_book_minimal(self, client):
        """Test creating a book with minimal data."""
        response = client.post(
            "/api/v1/books",
            json={"title": "Idylls of the King"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Idylls of the King"
        assert data["id"] is not None
        assert data["inventory_type"] == "PRIMARY"
        assert data["status"] == "ON_HAND"

    def test_create_book_full(self, client):
        """Test creating a book with all fields."""
        response = client.post(
            "/api/v1/books",
            json={
                "title": "In Memoriam",
                "publication_date": "1850",
                "volumes": 1,
                "category": "Victorian Poetry",
                "inventory_type": "PRIMARY",
                "binding_type": "Full morocco",
                "value_low": 200,
                "value_mid": 300,
                "value_high": 400,
                "status": "ON_HAND",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "In Memoriam"
        assert data["category"] == "Victorian Poetry"
        assert float(data["value_mid"]) == 300

    def test_create_book_missing_title(self, client):
        """Test that title is required."""
        response = client.post("/api/v1/books", json={})
        assert response.status_code == 422


class TestGetBook:
    """Tests for GET /api/v1/books/{id}."""

    def test_get_book_not_found(self, client):
        """Test 404 for non-existent book."""
        response = client.get("/api/v1/books/999")
        assert response.status_code == 404

    def test_get_book_exists(self, client):
        """Test getting a book that exists."""
        # Create a book first
        create_response = client.post(
            "/api/v1/books",
            json={"title": "Test Book"},
        )
        book_id = create_response.json()["id"]

        # Get it
        response = client.get(f"/api/v1/books/{book_id}")
        assert response.status_code == 200
        assert response.json()["title"] == "Test Book"


class TestUpdateBook:
    """Tests for PUT /api/v1/books/{id}."""

    def test_update_book(self, client):
        """Test updating a book."""
        # Create
        create_response = client.post(
            "/api/v1/books",
            json={"title": "Original Title"},
        )
        book_id = create_response.json()["id"]

        # Update
        response = client.put(
            f"/api/v1/books/{book_id}",
            json={"title": "Updated Title"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    def test_update_book_not_found(self, client):
        """Test 404 when updating non-existent book."""
        response = client.put("/api/v1/books/999", json={"title": "Test"})
        assert response.status_code == 404


class TestDeleteBook:
    """Tests for DELETE /api/v1/books/{id}."""

    def test_delete_book(self, client):
        """Test deleting a book."""
        # Create
        create_response = client.post(
            "/api/v1/books",
            json={"title": "To Delete"},
        )
        book_id = create_response.json()["id"]

        # Delete
        response = client.delete(f"/api/v1/books/{book_id}")
        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(f"/api/v1/books/{book_id}")
        assert get_response.status_code == 404


class TestBookStatus:
    """Tests for PATCH /api/v1/books/{id}/status."""

    def test_update_status(self, client):
        """Test updating book status."""
        # Create
        create_response = client.post(
            "/api/v1/books",
            json={"title": "Test", "status": "IN_TRANSIT"},
        )
        book_id = create_response.json()["id"]

        # Update status
        response = client.patch(f"/api/v1/books/{book_id}/status?status=ON_HAND")
        assert response.status_code == 200
        assert response.json()["status"] == "ON_HAND"

    def test_update_status_invalid(self, client):
        """Test invalid status value."""
        create_response = client.post(
            "/api/v1/books",
            json={"title": "Test"},
        )
        book_id = create_response.json()["id"]

        response = client.patch(f"/api/v1/books/{book_id}/status?status=INVALID")
        assert response.status_code == 400


class TestInventoryType:
    """Tests for PATCH /api/v1/books/{id}/inventory-type."""

    def test_update_inventory_type(self, client):
        """Test moving book between inventory types."""
        # Create in PRIMARY
        create_response = client.post(
            "/api/v1/books",
            json={"title": "Test", "inventory_type": "PRIMARY"},
        )
        book_id = create_response.json()["id"]

        # Move to FLAGGED
        response = client.patch(f"/api/v1/books/{book_id}/inventory-type?inventory_type=FLAGGED")
        assert response.status_code == 200
        assert response.json()["old_type"] == "PRIMARY"
        assert response.json()["new_type"] == "FLAGGED"


class TestAddTracking:
    """Tests for PATCH /api/v1/books/{id}/tracking."""

    def test_add_tracking_with_url(self, client):
        """Test adding tracking with direct URL."""
        # Create IN_TRANSIT book
        create_response = client.post(
            "/api/v1/books",
            json={"title": "Test Book", "status": "IN_TRANSIT"},
        )
        book_id = create_response.json()["id"]

        # Add tracking
        response = client.patch(
            f"/api/v1/books/{book_id}/tracking",
            json={
                "tracking_number": "12345",
                "tracking_carrier": "Custom",
                "tracking_url": "https://custom-tracker.com/12345",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tracking_number"] == "12345"
        assert data["tracking_carrier"] == "Custom"
        assert data["tracking_url"] == "https://custom-tracker.com/12345"

    def test_add_tracking_auto_detect_ups(self, client):
        """Test auto-detecting UPS carrier from tracking number."""
        # Create IN_TRANSIT book
        create_response = client.post(
            "/api/v1/books",
            json={"title": "Test Book", "status": "IN_TRANSIT"},
        )
        book_id = create_response.json()["id"]

        # Add tracking (UPS format)
        response = client.patch(
            f"/api/v1/books/{book_id}/tracking",
            json={"tracking_number": "1Z999AA10123456784"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tracking_number"] == "1Z999AA10123456784"
        assert data["tracking_carrier"] == "UPS"
        assert "ups.com" in data["tracking_url"]

    def test_add_tracking_auto_detect_usps(self, client):
        """Test auto-detecting USPS carrier from tracking number."""
        # Create IN_TRANSIT book
        create_response = client.post(
            "/api/v1/books",
            json={"title": "Test Book", "status": "IN_TRANSIT"},
        )
        book_id = create_response.json()["id"]

        # Add tracking (USPS format)
        response = client.patch(
            f"/api/v1/books/{book_id}/tracking",
            json={"tracking_number": "9400111899223100001234"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tracking_carrier"] == "USPS"
        assert "usps.com" in data["tracking_url"]

    def test_add_tracking_requires_in_transit(self, client):
        """Test that tracking can only be added to IN_TRANSIT books."""
        # Create ON_HAND book
        create_response = client.post(
            "/api/v1/books",
            json={"title": "Test Book", "status": "ON_HAND"},
        )
        book_id = create_response.json()["id"]

        # Try to add tracking
        response = client.patch(
            f"/api/v1/books/{book_id}/tracking",
            json={"tracking_url": "https://example.com/track"},
        )
        assert response.status_code == 400
        assert "IN_TRANSIT" in response.json()["detail"]

    def test_add_tracking_unknown_carrier_error(self, client):
        """Test error when carrier cannot be detected."""
        # Create IN_TRANSIT book
        create_response = client.post(
            "/api/v1/books",
            json={"title": "Test Book", "status": "IN_TRANSIT"},
        )
        book_id = create_response.json()["id"]

        # Try to add tracking with unknown format
        response = client.patch(
            f"/api/v1/books/{book_id}/tracking",
            json={"tracking_number": "INVALID123"},
        )
        assert response.status_code == 400
        assert "Could not detect carrier" in response.json()["detail"]

    def test_add_tracking_not_found(self, client):
        """Test 404 when book doesn't exist."""
        response = client.patch(
            "/api/v1/books/999/tracking",
            json={"tracking_url": "https://example.com/track"},
        )
        assert response.status_code == 404

    def test_add_tracking_empty_request(self, client):
        """Test that empty tracking request is rejected."""
        # Create IN_TRANSIT book
        create_response = client.post(
            "/api/v1/books",
            json={"title": "Test Book", "status": "IN_TRANSIT"},
        )
        book_id = create_response.json()["id"]

        # Try empty tracking
        response = client.patch(
            f"/api/v1/books/{book_id}/tracking",
            json={},
        )
        assert response.status_code == 400
        assert "tracking_number or tracking_url" in response.json()["detail"]

    def test_add_tracking_normalizes_number(self, client):
        """Test that tracking number is normalized (uppercase, no spaces)."""
        # Create IN_TRANSIT book
        create_response = client.post(
            "/api/v1/books",
            json={"title": "Test Book", "status": "IN_TRANSIT"},
        )
        book_id = create_response.json()["id"]

        # Add tracking with messy number
        response = client.patch(
            f"/api/v1/books/{book_id}/tracking",
            json={"tracking_number": "1z 999 aa1-0123-4567-84"},
        )
        assert response.status_code == 200
        data = response.json()
        # Should be normalized
        assert data["tracking_number"] == "1Z999AA10123456784"
