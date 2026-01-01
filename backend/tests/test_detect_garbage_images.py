"""Tests for detect_garbage_images function."""

import json
import logging
from unittest.mock import MagicMock, patch

from app.models import Book, BookImage
from app.services.eval_generation import detect_garbage_images


class TestDetectGarbageImages:
    """Tests for detect_garbage_images function."""

    def test_returns_indices_and_calls_delete(self, db):
        """Test that garbage indices are returned and delete_unrelated_images is called."""
        # Create a book with images
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        images = [
            BookImage(book_id=book.id, s3_key="img_0.jpg", display_order=0),
            BookImage(book_id=book.id, s3_key="img_1.jpg", display_order=1),
            BookImage(book_id=book.id, s3_key="img_2.jpg", display_order=2),
            BookImage(book_id=book.id, s3_key="img_3.jpg", display_order=3),
        ]
        for img in images:
            db.add(img)
        db.commit()
        db.refresh(book)

        # Mock Claude to return garbage indices [1, 3]
        mock_response = {
            "body": MagicMock(
                read=lambda: json.dumps(
                    {
                        "content": [
                            {"text": '{"garbage_indices": [1, 3]}'}
                        ]
                    }
                ).encode()
            )
        }

        with patch(
            "app.services.eval_generation.get_bedrock_client"
        ) as mock_client, patch(
            "app.services.eval_generation.fetch_book_images_for_bedrock"
        ) as mock_fetch, patch(
            "app.services.eval_generation.delete_unrelated_images"
        ) as mock_delete:
            mock_client.return_value.invoke_model.return_value = mock_response
            mock_fetch.return_value = [{"type": "image", "source": {}}]
            mock_delete.return_value = {"deleted_count": 2, "deleted_keys": [], "errors": []}

            result = detect_garbage_images(
                book_id=book.id,
                images=list(book.images),
                title="Test Book",
                author="Test Author",
                db=db,
            )

        # Should return the indices found
        assert result == [1, 3]

        # Should have called delete_unrelated_images with correct args
        mock_delete.assert_called_once()
        call_kwargs = mock_delete.call_args[1]
        assert call_kwargs["book_id"] == book.id
        assert call_kwargs["unrelated_indices"] == [1, 3]

    def test_all_valid_images_returns_empty(self, db):
        """Test that empty array is returned when all images are valid."""
        book = Book(title="Valid Book")
        db.add(book)
        db.commit()

        images = [
            BookImage(book_id=book.id, s3_key="img_0.jpg", display_order=0),
            BookImage(book_id=book.id, s3_key="img_1.jpg", display_order=1),
        ]
        for img in images:
            db.add(img)
        db.commit()
        db.refresh(book)

        # Mock Claude to return empty garbage_indices
        mock_response = {
            "body": MagicMock(
                read=lambda: json.dumps(
                    {
                        "content": [
                            {"text": '{"garbage_indices": []}'}
                        ]
                    }
                ).encode()
            )
        }

        with patch(
            "app.services.eval_generation.get_bedrock_client"
        ) as mock_client, patch(
            "app.services.eval_generation.fetch_book_images_for_bedrock"
        ) as mock_fetch, patch(
            "app.services.eval_generation.delete_unrelated_images"
        ) as mock_delete:
            mock_client.return_value.invoke_model.return_value = mock_response
            mock_fetch.return_value = [{"type": "image", "source": {}}]

            result = detect_garbage_images(
                book_id=book.id,
                images=list(book.images),
                title="Valid Book",
                author="Author",
                db=db,
            )

        # Should return empty list
        assert result == []

        # Should NOT call delete_unrelated_images when no garbage found
        mock_delete.assert_not_called()

    def test_claude_failure_returns_empty_and_logs_warning(self, db, caplog):
        """Test that Claude failure returns empty list and logs warning."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        images = [
            BookImage(book_id=book.id, s3_key="img_0.jpg", display_order=0),
        ]
        for img in images:
            db.add(img)
        db.commit()
        db.refresh(book)

        with patch(
            "app.services.eval_generation.get_bedrock_client"
        ) as mock_client, patch(
            "app.services.eval_generation.fetch_book_images_for_bedrock"
        ) as mock_fetch, patch(
            "app.services.eval_generation.delete_unrelated_images"
        ) as mock_delete:
            mock_client.return_value.invoke_model.side_effect = Exception(
                "Bedrock API error"
            )
            mock_fetch.return_value = [{"type": "image", "source": {}}]

            with caplog.at_level(logging.WARNING):
                result = detect_garbage_images(
                    book_id=book.id,
                    images=list(book.images),
                    title="Test Book",
                    author="Author",
                    db=db,
                )

        # Should return empty list on failure
        assert result == []

        # Should NOT call delete_unrelated_images on failure
        mock_delete.assert_not_called()

        # Should have logged a warning
        assert any("Garbage detection failed" in record.message for record in caplog.records)

    def test_no_images_returns_empty_without_calling_claude(self, db):
        """Test that empty image list returns empty without calling Claude."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        with patch(
            "app.services.eval_generation.get_bedrock_client"
        ) as mock_client, patch(
            "app.services.eval_generation.delete_unrelated_images"
        ) as mock_delete:
            result = detect_garbage_images(
                book_id=book.id,
                images=[],
                title="Test Book",
                author="Author",
                db=db,
            )

        # Should return empty list
        assert result == []

        # Should NOT have called Claude
        mock_client.return_value.invoke_model.assert_not_called()

        # Should NOT call delete_unrelated_images
        mock_delete.assert_not_called()

    def test_json_parse_failure_returns_empty_and_logs_warning(self, db, caplog):
        """Test that JSON parse failure returns empty list and logs warning."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        images = [
            BookImage(book_id=book.id, s3_key="img_0.jpg", display_order=0),
        ]
        for img in images:
            db.add(img)
        db.commit()
        db.refresh(book)

        # Mock Claude to return invalid JSON
        mock_response = {
            "body": MagicMock(
                read=lambda: json.dumps(
                    {
                        "content": [
                            {"text": "This is not valid JSON at all"}
                        ]
                    }
                ).encode()
            )
        }

        with patch(
            "app.services.eval_generation.get_bedrock_client"
        ) as mock_client, patch(
            "app.services.eval_generation.fetch_book_images_for_bedrock"
        ) as mock_fetch, patch(
            "app.services.eval_generation.delete_unrelated_images"
        ) as mock_delete:
            mock_client.return_value.invoke_model.return_value = mock_response
            mock_fetch.return_value = [{"type": "image", "source": {}}]

            with caplog.at_level(logging.WARNING):
                result = detect_garbage_images(
                    book_id=book.id,
                    images=list(book.images),
                    title="Test Book",
                    author="Author",
                    db=db,
                )

        # Should return empty list on parse failure
        assert result == []

        # Should NOT call delete_unrelated_images on failure
        mock_delete.assert_not_called()

        # Should have logged a warning
        assert any("Garbage detection failed" in record.message for record in caplog.records)

    def test_prompt_contains_title_and_author(self, db):
        """Test that the prompt sent to Claude contains the title and author."""
        book = Book(title="The Great Gatsby")
        db.add(book)
        db.commit()

        images = [
            BookImage(book_id=book.id, s3_key="img_0.jpg", display_order=0),
        ]
        for img in images:
            db.add(img)
        db.commit()
        db.refresh(book)

        mock_response = {
            "body": MagicMock(
                read=lambda: json.dumps(
                    {
                        "content": [
                            {"text": '{"garbage_indices": []}'}
                        ]
                    }
                ).encode()
            )
        }

        with patch(
            "app.services.eval_generation.get_bedrock_client"
        ) as mock_client, patch(
            "app.services.eval_generation.fetch_book_images_for_bedrock"
        ) as mock_fetch:
            mock_client.return_value.invoke_model.return_value = mock_response
            mock_fetch.return_value = [{"type": "image", "source": {}}]

            detect_garbage_images(
                book_id=book.id,
                images=list(book.images),
                title="The Great Gatsby",
                author="F. Scott Fitzgerald",
                db=db,
            )

        # Check the body passed to invoke_model
        call_args = mock_client.return_value.invoke_model.call_args
        body_json = json.loads(call_args[1]["body"])
        prompt_text = body_json["messages"][0]["content"][0]["text"]

        # Verify title and author are in the prompt
        assert "The Great Gatsby" in prompt_text
        assert "F. Scott Fitzgerald" in prompt_text
