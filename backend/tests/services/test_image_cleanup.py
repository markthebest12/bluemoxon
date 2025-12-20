"""Tests for image cleanup service."""

from unittest.mock import MagicMock, patch

from app.models import Book, BookImage
from app.services.image_cleanup import delete_unrelated_images


class TestDeleteUnrelatedImages:
    """Tests for delete_unrelated_images function."""

    def test_empty_indices_returns_early(self, db):
        """Empty unrelated_indices should return immediately."""
        result = delete_unrelated_images(
            book_id=1,
            unrelated_indices=[],
            unrelated_reasons={},
            db=db,
        )
        assert result["deleted_count"] == 0
        assert result["deleted_keys"] == []
        assert result["errors"] == []

    @patch("app.services.image_cleanup.boto3.client")
    def test_deletes_images_from_s3_and_db(self, mock_boto_client, db):
        """Should delete images from both S3 and database."""
        # Create mock S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        # Create a test book
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        # Add test images to book
        for i in range(5):
            img = BookImage(
                book_id=book.id,
                s3_key=f"books/{book.id}/image_{i:02d}.jpg",
                display_order=i,
            )
            db.add(img)
        db.commit()

        # Delete images at indices 3 and 4
        result = delete_unrelated_images(
            book_id=book.id,
            unrelated_indices=[3, 4],
            unrelated_reasons={"3": "Seller logo", "4": "Different book"},
            db=db,
        )

        assert result["deleted_count"] == 2
        assert len(result["deleted_keys"]) == 2
        assert f"books/{book.id}/image_03.jpg" in result["deleted_keys"]
        assert f"books/{book.id}/image_04.jpg" in result["deleted_keys"]
        assert result["errors"] == []

        # Verify S3 delete was called
        assert mock_s3.delete_object.call_count == 2

        # Verify database state - should have 3 remaining images
        remaining = db.query(BookImage).filter_by(book_id=book.id).all()
        assert len(remaining) == 3

        # Verify display_order was reordered (0, 1, 2)
        remaining_sorted = sorted(remaining, key=lambda x: x.display_order)
        assert remaining_sorted[0].display_order == 0
        assert remaining_sorted[1].display_order == 1
        assert remaining_sorted[2].display_order == 2

    @patch("app.services.image_cleanup.boto3.client")
    def test_invalid_index_adds_error(self, mock_boto_client, db):
        """Invalid indices should be logged as errors."""
        # Create mock S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        # Create a test book
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        # Add one test image
        img = BookImage(
            book_id=book.id,
            s3_key=f"books/{book.id}/image_00.jpg",
            display_order=0,
        )
        db.add(img)
        db.commit()

        # Try to delete with invalid index
        result = delete_unrelated_images(
            book_id=book.id,
            unrelated_indices=[99],  # Invalid - only has 1 image
            unrelated_reasons={},
            db=db,
        )

        assert result["deleted_count"] == 0
        assert result["deleted_keys"] == []
        assert len(result["errors"]) == 1
        assert "Invalid index 99" in result["errors"][0]

        # Verify S3 delete was NOT called
        assert mock_s3.delete_object.call_count == 0

        # Verify image still exists in database
        remaining = db.query(BookImage).filter_by(book_id=book.id).all()
        assert len(remaining) == 1

    @patch("app.services.image_cleanup.boto3.client")
    def test_no_images_returns_error(self, mock_boto_client, db):
        """Book with no images should return error."""
        # Create mock S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        # Create a book with no images
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        result = delete_unrelated_images(
            book_id=book.id,
            unrelated_indices=[0],
            unrelated_reasons={},
            db=db,
        )

        assert result["deleted_count"] == 0
        assert result["deleted_keys"] == []
        assert len(result["errors"]) == 1
        assert "No images found" in result["errors"][0]

        # Verify S3 delete was NOT called
        assert mock_s3.delete_object.call_count == 0

    @patch("app.services.image_cleanup.boto3.client")
    def test_s3_delete_failure_does_not_delete_from_db(self, mock_boto_client, db):
        """If S3 deletion fails, database record should not be deleted."""
        from botocore.exceptions import ClientError

        # Create mock S3 client that raises exception
        mock_s3 = MagicMock()
        mock_s3.delete_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Key not found"}}, "DeleteObject"
        )
        mock_boto_client.return_value = mock_s3

        # Create a test book with images
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        img = BookImage(
            book_id=book.id,
            s3_key=f"books/{book.id}/image_00.jpg",
            display_order=0,
        )
        db.add(img)
        db.commit()

        # Try to delete image
        result = delete_unrelated_images(
            book_id=book.id,
            unrelated_indices=[0],
            unrelated_reasons={"0": "Test reason"},
            db=db,
        )

        # Should have 0 successful deletions and 1 error
        assert result["deleted_count"] == 0
        assert result["deleted_keys"] == []
        assert len(result["errors"]) == 1
        assert "Failed to delete S3 object" in result["errors"][0]

        # Verify S3 delete was attempted
        assert mock_s3.delete_object.call_count == 1

        # Verify image still exists in database (not deleted because S3 failed)
        remaining = db.query(BookImage).filter_by(book_id=book.id).all()
        assert len(remaining) == 1

    @patch("app.services.image_cleanup.boto3.client")
    def test_mixed_valid_and_invalid_indices(self, mock_boto_client, db):
        """Should delete valid indices and log errors for invalid ones."""
        # Create mock S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        # Create a test book with 3 images
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        for i in range(3):
            img = BookImage(
                book_id=book.id,
                s3_key=f"books/{book.id}/image_{i:02d}.jpg",
                display_order=i,
            )
            db.add(img)
        db.commit()

        # Try to delete index 1 (valid) and index 99 (invalid)
        result = delete_unrelated_images(
            book_id=book.id,
            unrelated_indices=[1, 99],
            unrelated_reasons={"1": "Valid deletion", "99": "Invalid index"},
            db=db,
        )

        # Should have 1 successful deletion and 1 error
        assert result["deleted_count"] == 1
        assert len(result["deleted_keys"]) == 1
        assert f"books/{book.id}/image_01.jpg" in result["deleted_keys"]
        assert len(result["errors"]) == 1
        assert "Invalid index 99" in result["errors"][0]

        # Verify S3 delete was called once (for valid index)
        assert mock_s3.delete_object.call_count == 1

        # Verify 2 images remain
        remaining = db.query(BookImage).filter_by(book_id=book.id).all()
        assert len(remaining) == 2

    @patch("app.services.image_cleanup.boto3.client")
    def test_uses_unrelated_reasons_in_logging(self, mock_boto_client, db):
        """Should use provided reasons from unrelated_reasons dict."""
        # Create mock S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        # Create a test book with images
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        img = BookImage(
            book_id=book.id,
            s3_key=f"books/{book.id}/image_00.jpg",
            display_order=0,
        )
        db.add(img)
        db.commit()

        # Delete with custom reason
        result = delete_unrelated_images(
            book_id=book.id,
            unrelated_indices=[0],
            unrelated_reasons={"0": "Seller promotional banner"},
            db=db,
        )

        # Should succeed
        assert result["deleted_count"] == 1
        assert result["errors"] == []

    @patch("app.services.image_cleanup.boto3.client")
    def test_reorders_remaining_images_after_deletion(self, mock_boto_client, db):
        """Remaining images should be reordered sequentially after deletion."""
        # Create mock S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        # Create a test book with 5 images
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        for i in range(5):
            img = BookImage(
                book_id=book.id,
                s3_key=f"books/{book.id}/image_{i:02d}.jpg",
                display_order=i,
            )
            db.add(img)
        db.commit()

        # Delete images at indices 1 and 3 (middle deletions)
        result = delete_unrelated_images(
            book_id=book.id,
            unrelated_indices=[1, 3],
            unrelated_reasons={},
            db=db,
        )

        # Should have deleted 2 images
        assert result["deleted_count"] == 2

        # Verify remaining images have sequential display_order
        remaining = (
            db.query(BookImage).filter_by(book_id=book.id).order_by(BookImage.display_order).all()
        )
        assert len(remaining) == 3
        assert remaining[0].display_order == 0
        assert remaining[1].display_order == 1
        assert remaining[2].display_order == 2

        # Verify the correct images remain (original indices 0, 2, 4)
        assert remaining[0].s3_key == f"books/{book.id}/image_00.jpg"
        assert remaining[1].s3_key == f"books/{book.id}/image_02.jpg"
        assert remaining[2].s3_key == f"books/{book.id}/image_04.jpg"
