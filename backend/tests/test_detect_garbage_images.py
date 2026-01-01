"""Tests for detect_garbage_images function."""

import json
import logging
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

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
                    {"content": [{"text": '{"garbage_indices": [1, 3]}'}]}
                ).encode()
            )
        }

        with (
            patch("app.services.eval_generation.get_bedrock_client") as mock_client,
            patch("app.services.eval_generation.fetch_book_images_for_bedrock") as mock_fetch,
            patch("app.services.eval_generation.delete_unrelated_images") as mock_delete,
        ):
            mock_client.return_value.invoke_model.return_value = mock_response
            # Return 4 image blocks to match the 4 images - validation uses this count
            mock_fetch.return_value = [
                {"type": "image", "source": {}},
                {"type": "image", "source": {}},
                {"type": "image", "source": {}},
                {"type": "image", "source": {}},
            ]
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
                read=lambda: json.dumps({"content": [{"text": '{"garbage_indices": []}'}]}).encode()
            )
        }

        with (
            patch("app.services.eval_generation.get_bedrock_client") as mock_client,
            patch("app.services.eval_generation.fetch_book_images_for_bedrock") as mock_fetch,
            patch("app.services.eval_generation.delete_unrelated_images") as mock_delete,
        ):
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

        with (
            patch("app.services.eval_generation.get_bedrock_client") as mock_client,
            patch("app.services.eval_generation.fetch_book_images_for_bedrock") as mock_fetch,
            patch("app.services.eval_generation.delete_unrelated_images") as mock_delete,
        ):
            mock_client.return_value.invoke_model.side_effect = Exception("Bedrock API error")
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

        with (
            patch("app.services.eval_generation.get_bedrock_client") as mock_client,
            patch("app.services.eval_generation.delete_unrelated_images") as mock_delete,
        ):
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
                    {"content": [{"text": "This is not valid JSON at all"}]}
                ).encode()
            )
        }

        with (
            patch("app.services.eval_generation.get_bedrock_client") as mock_client,
            patch("app.services.eval_generation.fetch_book_images_for_bedrock") as mock_fetch,
            patch("app.services.eval_generation.delete_unrelated_images") as mock_delete,
        ):
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
                read=lambda: json.dumps({"content": [{"text": '{"garbage_indices": []}'}]}).encode()
            )
        }

        with (
            patch("app.services.eval_generation.get_bedrock_client") as mock_client,
            patch("app.services.eval_generation.fetch_book_images_for_bedrock") as mock_fetch,
        ):
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

    def test_filters_invalid_indices(self, db, caplog):
        """Test that invalid indices (out-of-bounds, non-integers) are filtered.

        Note: Validation is against len(image_blocks) - the count of images
        actually sent to Claude, not the original image count.
        """
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        # Create 4 images (valid indices are 0, 1, 2, 3)
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

        # Mock Claude to return invalid indices: -1 (negative), 99 (out of bounds),
        # "foo" (string), 1.5 (float), plus valid indices 1 and 3
        mock_response = {
            "body": MagicMock(
                read=lambda: json.dumps(
                    {"content": [{"text": '{"garbage_indices": [-1, 1, 99, "foo", 1.5, 3]}'}]}
                ).encode()
            )
        }

        with (
            patch("app.services.eval_generation.get_bedrock_client") as mock_client,
            patch("app.services.eval_generation.fetch_book_images_for_bedrock") as mock_fetch,
            patch("app.services.eval_generation.delete_unrelated_images") as mock_delete,
        ):
            mock_client.return_value.invoke_model.return_value = mock_response
            # Return 4 image blocks to match the 4 images - validation uses this count
            mock_fetch.return_value = [
                {"type": "image", "source": {}},
                {"type": "image", "source": {}},
                {"type": "image", "source": {}},
                {"type": "image", "source": {}},
            ]
            mock_delete.return_value = {"deleted_count": 2, "deleted_keys": [], "errors": []}

            with caplog.at_level(logging.WARNING):
                result = detect_garbage_images(
                    book_id=book.id,
                    images=list(book.images),
                    title="Test Book",
                    author="Test Author",
                    db=db,
                )

        # Should only return valid indices [1, 3]
        assert result == [1, 3]

        # Should have called delete with only valid indices
        mock_delete.assert_called_once()
        call_kwargs = mock_delete.call_args[1]
        assert call_kwargs["unrelated_indices"] == [1, 3]

        # Should have logged a warning about filtered indices
        assert any("Filtered 4 invalid indices" in record.message for record in caplog.records)

    def test_all_indices_invalid_returns_empty(self, db, caplog):
        """Test that when all returned indices are invalid, returns empty list.

        Note: Validation is against len(image_blocks) - the count of images
        actually sent to Claude, not the original image count.
        """
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        # Create 2 images (valid indices are 0, 1)
        images = [
            BookImage(book_id=book.id, s3_key="img_0.jpg", display_order=0),
            BookImage(book_id=book.id, s3_key="img_1.jpg", display_order=1),
        ]
        for img in images:
            db.add(img)
        db.commit()
        db.refresh(book)

        # Mock Claude to return only invalid indices
        mock_response = {
            "body": MagicMock(
                read=lambda: json.dumps(
                    {"content": [{"text": '{"garbage_indices": [-1, 99, "bad"]}'}]}
                ).encode()
            )
        }

        with (
            patch("app.services.eval_generation.get_bedrock_client") as mock_client,
            patch("app.services.eval_generation.fetch_book_images_for_bedrock") as mock_fetch,
            patch("app.services.eval_generation.delete_unrelated_images") as mock_delete,
        ):
            mock_client.return_value.invoke_model.return_value = mock_response
            # Return 2 image blocks to match the 2 images - validation uses this count
            mock_fetch.return_value = [
                {"type": "image", "source": {}},
                {"type": "image", "source": {}},
            ]

            with caplog.at_level(logging.WARNING):
                result = detect_garbage_images(
                    book_id=book.id,
                    images=list(book.images),
                    title="Test Book",
                    author="Test Author",
                    db=db,
                )

        # Should return empty list since all indices were invalid
        assert result == []

        # Should NOT have called delete since no valid indices
        mock_delete.assert_not_called()

        # Should have logged warning about filtered indices
        assert any("Filtered 3 invalid indices" in record.message for record in caplog.records)

    def test_retries_on_throttling(self, db, caplog):
        """Test that throttling errors trigger retries with eventual success."""
        book = Book(title="Test Book")
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

        # Create throttling error
        throttle_error = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
            "InvokeModel",
        )

        # Success response after throttling
        success_response = {
            "body": MagicMock(
                read=lambda: json.dumps(
                    {"content": [{"text": '{"garbage_indices": [1]}'}]}
                ).encode()
            )
        }

        with (
            patch("app.services.eval_generation.get_bedrock_client") as mock_client,
            patch("app.services.eval_generation.fetch_book_images_for_bedrock") as mock_fetch,
            patch("app.services.eval_generation.delete_unrelated_images") as mock_delete,
            patch("app.services.eval_generation.time.sleep") as mock_sleep,
        ):
            # First call throttles, second succeeds
            mock_client.return_value.invoke_model.side_effect = [
                throttle_error,
                success_response,
            ]
            # Return 2 image blocks to match the 2 images - validation uses this count
            mock_fetch.return_value = [
                {"type": "image", "source": {}},
                {"type": "image", "source": {}},
            ]
            mock_delete.return_value = {"deleted_count": 1, "deleted_keys": [], "errors": []}

            with caplog.at_level(logging.WARNING):
                result = detect_garbage_images(
                    book_id=book.id,
                    images=list(book.images),
                    title="Test Book",
                    author="Test Author",
                    db=db,
                    max_retries=3,
                    base_delay=0.1,
                )

        # Should succeed on retry
        assert result == [1]

        # Should have called invoke_model twice (throttled once, then succeeded)
        assert mock_client.return_value.invoke_model.call_count == 2

        # Should have slept once (before retry)
        assert mock_sleep.call_count == 1

        # Should have logged throttling warning
        assert any("throttled" in record.message.lower() for record in caplog.records)

    def test_gives_up_after_max_retries(self, db, caplog):
        """Test that function gives up after max retries exhausted."""
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

        # Create throttling error that persists
        throttle_error = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
            "InvokeModel",
        )

        with (
            patch("app.services.eval_generation.get_bedrock_client") as mock_client,
            patch("app.services.eval_generation.fetch_book_images_for_bedrock") as mock_fetch,
            patch("app.services.eval_generation.delete_unrelated_images") as mock_delete,
            patch("app.services.eval_generation.time.sleep") as mock_sleep,
        ):
            # Always throttle
            mock_client.return_value.invoke_model.side_effect = throttle_error
            mock_fetch.return_value = [{"type": "image", "source": {}}]

            with caplog.at_level(logging.WARNING):
                result = detect_garbage_images(
                    book_id=book.id,
                    images=list(book.images),
                    title="Test Book",
                    author="Test Author",
                    db=db,
                    max_retries=2,
                    base_delay=0.1,
                )

        # Should return empty list after exhausting retries
        assert result == []

        # Should have tried 3 times (initial + 2 retries)
        assert mock_client.return_value.invoke_model.call_count == 3

        # Should have slept twice (before each retry)
        assert mock_sleep.call_count == 2

        # Should NOT have called delete since it failed
        mock_delete.assert_not_called()

        # Should have logged throttling warnings and final failure
        assert any("throttled" in record.message.lower() for record in caplog.records)
        assert any(
            "garbage detection failed" in record.message.lower() for record in caplog.records
        )

    def test_validates_against_fetched_count_not_original(self, db, caplog):
        """Test that index validation uses fetched image count, not original count.

        This tests the P0 bug fix: If book has 30 images but only 20 are sent to
        Claude (due to max_images limit), Claude indexes 0-19. If Claude returns
        index 25, it should be filtered as invalid (>= 20), not accepted as valid
        (< 30).
        """
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        # Create 30 images
        images = []
        for i in range(30):
            img = BookImage(book_id=book.id, s3_key=f"img_{i}.jpg", display_order=i)
            db.add(img)
            images.append(img)
        db.commit()
        db.refresh(book)

        # Claude returns indices that would be valid for 30 images (0-29)
        # but invalid for 20 images (0-19)
        mock_response = {
            "body": MagicMock(
                read=lambda: json.dumps(
                    {
                        "content": [
                            # Indices 5, 25, 28 - only 5 is valid for 20 images
                            {"text": '{"garbage_indices": [5, 25, 28]}'}
                        ]
                    }
                ).encode()
            )
        }

        with (
            patch("app.services.eval_generation.get_bedrock_client") as mock_client,
            patch("app.services.eval_generation.fetch_book_images_for_bedrock") as mock_fetch,
            patch("app.services.eval_generation.delete_unrelated_images") as mock_delete,
        ):
            mock_client.return_value.invoke_model.return_value = mock_response
            # Only 20 images are sent to Claude (due to max_images=20)
            mock_fetch.return_value = [{"type": "image", "source": {}} for _ in range(20)]
            mock_delete.return_value = {"deleted_count": 1, "deleted_keys": [], "errors": []}

            with caplog.at_level(logging.WARNING):
                result = detect_garbage_images(
                    book_id=book.id,
                    images=list(book.images),  # 30 images
                    title="Test Book",
                    author="Test Author",
                    db=db,
                )

        # Should only return index 5 (valid for 20 images)
        # Indices 25 and 28 should be filtered (>= 20)
        assert result == [5]

        # Should have called delete with only valid index
        mock_delete.assert_called_once()
        call_kwargs = mock_delete.call_args[1]
        assert call_kwargs["unrelated_indices"] == [5]

        # Should have logged warning about filtered indices
        assert any("Filtered 2 invalid indices" in record.message for record in caplog.records)
