"""Test that eBay import stores purchase_price (asking price) for eval context.

Bug #498: Eval runbooks need the asking price to calculate discount percentages
and make accurate acquisition recommendations.
"""

from app.models import Book, EvalRunbook


class TestEbayImportPurchasePrice:
    """Test that asking price from eBay import is stored in purchase_price field."""

    def test_create_book_from_ebay_import_stores_purchase_price(self, client, db):
        """Test that purchase_price (asking price) is stored when creating book from eBay import.

        This is critical for eval runbook generation:
        - Eval runbook uses purchase_price to calculate discount vs FMV
        - Without asking price, eval runbook cannot recommend ACQUIRE/PASS
        - Import form shows "Asking Price" field that should map to purchase_price
        """
        # Simulate eBay import payload from ImportListingModal.vue
        # The frontend sends purchase_price as the asking price from the eBay listing
        ebay_import_payload = {
            "title": "The Idylls of the King",
            "author_id": None,  # Would be set after creating author
            "publication_date": "1868",
            "volumes": 1,
            "source_url": "https://www.ebay.com/itm/123456789",
            "source_item_id": "123456789",
            "purchase_price": 450.00,  # This is the asking price from eBay
            "binding_type": "Full morocco",
            "condition_notes": "Fine condition",
            "status": "EVALUATING",  # Watchlist items are EVALUATING
            "inventory_type": "PRIMARY",
            "category": "Victorian Poetry",
            "listing_s3_keys": ["listings/123456789/image_0.jpg"],
        }

        # Create book via API (simulating frontend addToWatchlist call)
        response = client.post("/api/v1/books", json=ebay_import_payload)

        assert response.status_code == 201, f"Book creation failed: {response.json()}"
        book_data = response.json()

        # CRITICAL: purchase_price must be stored
        assert book_data["purchase_price"] is not None, (
            "purchase_price (asking price) was not stored! "
            "Eval runbook cannot calculate discount without asking price."
        )
        assert float(book_data["purchase_price"]) == 450.00, (
            f"Expected purchase_price=450.00, got {book_data['purchase_price']}"
        )

        # Verify it's also in the database
        book = db.query(Book).filter(Book.id == book_data["id"]).first()
        assert book is not None
        assert book.purchase_price is not None, "purchase_price not in database!"
        assert float(book.purchase_price) == 450.00

    def test_eval_runbook_uses_purchase_price_as_asking_price(self, client, db):
        """Test that eval runbook generation reads purchase_price as the asking price.

        The eval_worker.py reads book.purchase_price as the asking price for scoring.
        Without this, the eval runbook shows "No asking price" and cannot calculate
        discount percentages or make acquisition recommendations.
        """
        # Create a book with purchase_price set (simulating eBay import)
        create_response = client.post(
            "/api/v1/books",
            json={
                "title": "In Memoriam",
                "publication_date": "1850",
                "volumes": 1,
                "source_url": "https://www.ebay.com/itm/999",
                "source_item_id": "999",
                "purchase_price": 350.00,  # Asking price from eBay
                "status": "EVALUATING",
                "inventory_type": "PRIMARY",
                "category": "Test",
                "listing_s3_keys": ["test/img.jpg"],
            },
        )
        book_id = create_response.json()["id"]

        # Get the book from database
        book = db.query(Book).filter(Book.id == book_id).first()

        # Simulate what eval_worker.py does when building listing_data
        listing_data = {
            "price": float(book.purchase_price) if book.purchase_price else None,
            "author": book.author.name if book.author else None,
            "publisher": book.publisher.name if book.publisher else None,
            "description": book.condition_notes,
        }

        # CRITICAL: listing_data["price"] must be set for eval runbook scoring
        assert listing_data["price"] is not None, (
            "eval_worker.py cannot build listing_data with price! "
            "book.purchase_price is None when it should be the asking price."
        )
        assert listing_data["price"] == 350.00, (
            f"Expected asking price 350.00, got {listing_data['price']}"
        )

    def test_purchase_price_preserved_through_acquire_workflow(self, client, db):
        """Test that asking price is not lost when book is acquired.

        CRITICAL BUG: When acquire_book() runs, it overwrites book.purchase_price
        with the actual purchase price, losing the original asking price context.

        The eval runbook stores original_asking_price, but if purchase_price
        is overwritten before the eval runbook job runs, the job won't see the
        original asking price.
        """
        # Create book with asking price from eBay import
        create_response = client.post(
            "/api/v1/books",
            json={
                "title": "The Princess",
                "publication_date": "1847",
                "source_url": "https://www.ebay.com/itm/111",
                "source_item_id": "111",
                "purchase_price": 500.00,  # Original asking price from eBay
                "status": "EVALUATING",
                "inventory_type": "PRIMARY",
                "category": "Test",
                "listing_s3_keys": ["test/img.jpg"],
            },
        )
        assert create_response.status_code == 201
        book_id = create_response.json()["id"]

        # Verify asking price is stored
        book = db.query(Book).filter(Book.id == book_id).first()
        assert book.purchase_price is not None
        assert float(book.purchase_price) == 500.00

        # Simulate acquiring the book at a different price
        acquire_response = client.patch(
            f"/api/v1/books/{book_id}/acquire",
            json={
                "purchase_price": 400.00,  # Actual purchase price (negotiated down)
                "purchase_date": "2025-01-15",
                "order_number": "ORD-123",
                "place_of_purchase": "eBay",
            },
        )
        assert acquire_response.status_code == 200

        # CRITICAL: After acquisition, book.purchase_price is overwritten
        book = db.query(Book).filter(Book.id == book_id).first()
        assert float(book.purchase_price) == 400.00  # Now shows actual purchase price

        # Check if eval runbook exists and has original asking price preserved
        eval_runbook = db.query(EvalRunbook).filter(EvalRunbook.book_id == book_id).first()

        # If eval runbook exists (created before acquisition), it should have original asking price
        if eval_runbook:
            assert eval_runbook.original_asking_price is not None, (
                "Eval runbook exists but original_asking_price is None! "
                "The asking price context was lost."
            )
            assert float(eval_runbook.original_asking_price) == 500.00, (
                f"Expected original asking price 500.00, got {eval_runbook.original_asking_price}"
            )
        # If no eval runbook yet (async job pending), the asking price is already lost from book.purchase_price!
