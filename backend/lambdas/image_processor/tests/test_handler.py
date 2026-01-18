"""Unit tests for image processor Lambda handler."""

from unittest.mock import MagicMock, patch

from PIL import Image as PILImage


class TestSmokeTest:
    """Tests for smoke test functionality."""

    def test_smoke_test_returns_ok(self, smoke_test_event):
        """Smoke test endpoint returns 200 OK."""
        from handler import lambda_handler

        result = lambda_handler(smoke_test_event, None)

        assert result["statusCode"] == 200
        assert result["body"] == "OK"

    def test_smoke_test_includes_version(self, smoke_test_event, monkeypatch):
        """Smoke test includes Lambda function version."""
        monkeypatch.setenv("AWS_LAMBDA_FUNCTION_VERSION", "$LATEST")
        from handler import lambda_handler

        result = lambda_handler(smoke_test_event, None)

        assert result["version"] == "$LATEST"


class TestSQSEventParsing:
    """Tests for SQS event parsing."""

    def test_sqs_event_parsing_returns_batch_failures_key(self, sqs_event):
        """Handler correctly returns batchItemFailures structure."""
        with patch("handler.process_image", return_value=True):
            from handler import lambda_handler

            result = lambda_handler(sqs_event, None)

            assert "batchItemFailures" in result
            assert isinstance(result["batchItemFailures"], list)

    def test_sqs_event_empty_records(self):
        """Handler handles empty Records list."""
        from handler import lambda_handler

        result = lambda_handler({"Records": []}, None)

        assert result == {"batchItemFailures": []}

    def test_sqs_event_extracts_job_data(self, sqs_event):
        """Handler correctly extracts job_id, book_id, image_id from message."""
        captured_args = []

        def capture_args(job_id, book_id, image_id):
            captured_args.append((job_id, book_id, image_id))
            return True

        with patch("handler.process_image", side_effect=capture_args):
            from handler import lambda_handler

            lambda_handler(sqs_event, None)

            assert len(captured_args) == 1
            assert captured_args[0] == ("job-456", 123, 789)

    def test_sqs_event_invalid_json_adds_to_failures(self):
        """Invalid JSON in message body adds to failures."""
        from handler import lambda_handler

        event = {
            "Records": [
                {
                    "messageId": "msg-bad",
                    "body": "not valid json",
                }
            ]
        }

        result = lambda_handler(event, None)

        assert len(result["batchItemFailures"]) == 1
        assert result["batchItemFailures"][0]["itemIdentifier"] == "msg-bad"

    def test_sqs_event_processing_failure_adds_to_failures(self, sqs_event):
        """Failed processing adds message to failures."""
        with patch("handler.process_image", return_value=False):
            from handler import lambda_handler

            result = lambda_handler(sqs_event, None)

            assert len(result["batchItemFailures"]) == 1
            assert result["batchItemFailures"][0]["itemIdentifier"] == "msg-123"

    def test_sqs_multiple_records_partial_failure(self, sqs_event_multiple):
        """Handler correctly reports partial batch failures."""
        call_count = [0]

        def alternating_result(job_id, book_id, image_id):
            call_count[0] += 1
            return call_count[0] == 1

        with patch("handler.process_image", side_effect=alternating_result):
            from handler import lambda_handler

            result = lambda_handler(sqs_event_multiple, None)

            assert len(result["batchItemFailures"]) == 1
            assert result["batchItemFailures"][0]["itemIdentifier"] == "msg-2"


class TestBrightnessSelection:
    """Tests for brightness-based background selection."""

    def test_brightness_below_threshold_selects_black(self):
        """Brightness below 128 selects black background."""
        from handler import select_background_color

        assert select_background_color(50) == "black"
        assert select_background_color(0) == "black"
        assert select_background_color(127) == "black"

    def test_brightness_at_threshold_selects_white(self):
        """Brightness at 128 selects white background."""
        from handler import select_background_color

        assert select_background_color(128) == "white"

    def test_brightness_above_threshold_selects_white(self):
        """Brightness above 128 selects white background."""
        from handler import select_background_color

        assert select_background_color(200) == "white"
        assert select_background_color(255) == "white"


class TestProcessingConfig:
    """Tests for processing configuration by attempt."""

    def test_first_attempt_uses_u2net(self):
        """First attempt uses u2net with alpha matting."""
        from handler import get_processing_config

        config = get_processing_config(1)

        assert config["model"] == "u2net"
        assert config["alpha_matting"] is True
        assert config["model_name"] == "u2net-alpha"

    def test_second_attempt_uses_u2net(self):
        """Second attempt also uses u2net with alpha matting."""
        from handler import get_processing_config

        config = get_processing_config(2)

        assert config["model"] == "u2net"
        assert config["alpha_matting"] is True

    def test_third_attempt_uses_isnet(self):
        """Third attempt uses isnet-general-use without alpha matting."""
        from handler import get_processing_config

        config = get_processing_config(3)

        assert config["model"] == "isnet-general-use"
        assert config["alpha_matting"] is False
        assert config["model_name"] == "isnet-general-use"


class TestCalculateBrightness:
    """Tests for brightness calculation."""

    def test_white_image_brightness(self):
        """White image has high brightness."""
        from handler import calculate_brightness

        img = PILImage.new("RGBA", (10, 10), (255, 255, 255, 255))
        brightness = calculate_brightness(img)

        assert brightness == 255

    def test_black_image_brightness(self):
        """Black image has zero brightness."""
        from handler import calculate_brightness

        img = PILImage.new("RGBA", (10, 10), (0, 0, 0, 255))
        brightness = calculate_brightness(img)

        assert brightness == 0

    def test_gray_image_brightness(self):
        """Gray image has medium brightness."""
        from handler import calculate_brightness

        img = PILImage.new("RGBA", (10, 10), (128, 128, 128, 255))
        brightness = calculate_brightness(img)

        assert 127 <= brightness <= 129

    def test_transparent_pixels_ignored(self):
        """Fully transparent pixels are ignored in brightness calculation."""
        from handler import calculate_brightness

        img = PILImage.new("RGBA", (10, 10), (0, 0, 0, 0))
        brightness = calculate_brightness(img)

        assert brightness == 128


class TestAddBackground:
    """Tests for adding background to images."""

    def test_add_black_background(self):
        """Black background is correctly applied."""
        from handler import add_background

        img = PILImage.new("RGBA", (10, 10), (255, 0, 0, 255))
        result = add_background(img, "black")

        assert result.mode == "RGB"
        assert result.getpixel((0, 0)) == (255, 0, 0)

    def test_add_white_background(self):
        """White background is correctly applied."""
        from handler import add_background

        img = PILImage.new("RGBA", (10, 10), (0, 255, 0, 255))
        result = add_background(img, "white")

        assert result.mode == "RGB"
        assert result.getpixel((0, 0)) == (0, 255, 0)

    def test_transparent_area_gets_background(self):
        """Transparent areas receive the background color."""
        from handler import add_background

        img = PILImage.new("RGBA", (10, 10), (0, 0, 0, 0))
        result = add_background(img, "white")

        assert result.getpixel((0, 0)) == (255, 255, 255)


class TestCalculateSubjectBounds:
    """Tests for subject bounding box calculation."""

    def test_full_opaque_image(self):
        """Fully opaque image returns full bounds."""
        from handler import calculate_subject_bounds

        img = PILImage.new("RGBA", (100, 100), (255, 0, 0, 255))
        bounds = calculate_subject_bounds(img)

        assert bounds == (0, 0, 100, 100)

    def test_fully_transparent_image(self):
        """Fully transparent image returns None."""
        from handler import calculate_subject_bounds

        img = PILImage.new("RGBA", (100, 100), (0, 0, 0, 0))
        bounds = calculate_subject_bounds(img)

        assert bounds is None

    def test_non_rgba_image_returns_full_bounds(self):
        """Non-RGBA image returns full image bounds."""
        from handler import calculate_subject_bounds

        img = PILImage.new("RGB", (100, 100), (255, 0, 0))
        bounds = calculate_subject_bounds(img)

        assert bounds == (0, 0, 100, 100)


class TestProcessImageJobStatusUpdates:
    """Tests for job status updates during processing."""

    def test_missing_job_returns_false(self, mock_environment):
        """Processing returns False when job not found."""
        import handler

        mock_job_model = MagicMock()
        mock_image_model = MagicMock()

        with patch("handler.get_db_session") as mock_get_session:
            mock_session = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = None
            mock_get_session.return_value = mock_session

            with patch.object(handler, "ImageProcessingJob", mock_job_model):
                with patch.object(handler, "BookImage", mock_image_model):
                    with patch.object(handler, "_models_loaded", True):
                        result = handler.process_image("nonexistent-job", 123, 789)

                        assert result is False

    def test_no_images_for_book_marks_job_failed(self, mock_environment, mock_processing_job):
        """Job marked failed when no images found for book."""
        import handler

        mock_job_model = MagicMock()
        mock_image_model = MagicMock()

        with patch("handler.get_db_session") as mock_get_session:
            mock_session = MagicMock()
            # First query returns the job, second returns empty list for book images
            mock_session.query.return_value.filter.return_value.first.return_value = (
                mock_processing_job
            )
            # Mock the with_for_update() chain for book images query
            mock_session.query.return_value.filter.return_value.with_for_update.return_value.all.return_value = []
            mock_get_session.return_value = mock_session

            with patch.object(handler, "ImageProcessingJob", mock_job_model):
                with patch.object(handler, "BookImage", mock_image_model):
                    with patch.object(handler, "_models_loaded", True):
                        result = handler.process_image("job-456", 123, 789)

                        assert result is False
                        assert mock_processing_job.status == "failed"
                        assert mock_processing_job.failure_reason == "No images found for book"

    def test_job_status_completed_on_success(
        self, mock_environment, mock_processing_job, mock_book_image
    ):
        """Job status is set to completed with completed_at timestamp on success."""
        import handler

        mock_job_model = MagicMock()
        mock_image_model = MagicMock()

        mock_rgba_image = PILImage.new("RGBA", (100, 100), (128, 128, 128, 255))

        with patch("handler.get_db_session") as mock_get_session:
            mock_session = MagicMock()
            mock_session.query.return_value.filter.return_value.first.side_effect = [
                mock_processing_job,
                mock_book_image,
            ]
            # Mock with_for_update() chain for book images query
            mock_session.query.return_value.filter.return_value.with_for_update.return_value.all.return_value = [
                mock_book_image
            ]
            mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
            mock_session.query.return_value.filter.return_value.scalar.return_value = 0
            mock_get_session.return_value = mock_session

            with patch.object(handler, "ImageProcessingJob", mock_job_model):
                with patch.object(handler, "BookImage", mock_image_model):
                    with patch.object(handler, "_models_loaded", True):
                        with patch("handler.download_from_s3") as mock_download:
                            mock_download.return_value = b"fake-image-bytes"
                            with patch("handler.Image.open") as mock_open:
                                mock_open.return_value = mock_rgba_image
                                with patch("handler.remove_background") as mock_remove_bg:
                                    mock_remove_bg.return_value = {
                                        "image": mock_rgba_image,
                                        "subject_width": 90,
                                        "subject_height": 90,
                                    }
                                    with patch("handler.upload_to_s3"):
                                        result = handler.process_image("job-456", 123, 789)

                                        assert result is True
                                        assert mock_processing_job.status == "completed"
                                        assert mock_processing_job.completed_at is not None


class TestThumbnailGeneration:
    """Tests for thumbnail generation."""

    def test_generate_thumbnail_creates_jpeg(self):
        """Should create a JPEG thumbnail from PNG."""
        from handler import generate_thumbnail

        # Create a test RGBA image (100x150)
        test_image = PILImage.new("RGBA", (100, 150), (255, 0, 0, 255))

        thumbnail = generate_thumbnail(test_image)

        assert thumbnail is not None
        assert thumbnail.mode == "RGB"  # JPEG doesn't support alpha
        assert thumbnail.size[0] <= 300
        assert thumbnail.size[1] <= 300

    def test_generate_thumbnail_maintains_aspect_ratio(self):
        """Should maintain aspect ratio when resizing."""
        from handler import generate_thumbnail

        # Create a tall image (200x400)
        test_image = PILImage.new("RGB", (200, 400), (0, 255, 0))

        thumbnail = generate_thumbnail(test_image)

        # Should be 150x300 (scaled to fit 300x300 maintaining ratio)
        assert thumbnail.size == (150, 300)

    def test_generate_thumbnail_handles_small_images(self):
        """Should not upscale small images."""
        from handler import generate_thumbnail

        # Create a small image (50x50)
        test_image = PILImage.new("RGB", (50, 50), (0, 0, 255))

        thumbnail = generate_thumbnail(test_image)

        # Should stay 50x50, not upscaled
        assert thumbnail.size == (50, 50)


class TestSourceImageSelection:
    """Tests for smart source image selection."""

    def test_selects_title_page_over_others(self):
        """Should select title_page type if available."""
        from handler import select_best_source_image

        images = [
            MagicMock(id=1, image_type="cover", is_primary=True, is_background_processed=False),
            MagicMock(
                id=2, image_type="title_page", is_primary=False, is_background_processed=False
            ),
            MagicMock(id=3, image_type="interior", is_primary=False, is_background_processed=False),
        ]

        result = select_best_source_image(images, primary_image_id=1)
        assert result.id == 2

    def test_selects_binding_when_no_title_page(self):
        """Should select binding type if no title_page."""
        from handler import select_best_source_image

        images = [
            MagicMock(id=1, image_type="interior", is_primary=True, is_background_processed=False),
            MagicMock(id=2, image_type="binding", is_primary=False, is_background_processed=False),
            MagicMock(id=3, image_type=None, is_primary=False, is_background_processed=False),
        ]

        result = select_best_source_image(images, primary_image_id=1)
        assert result.id == 2

    def test_selects_cover_when_no_binding(self):
        """Should select cover type if no title_page or binding."""
        from handler import select_best_source_image

        images = [
            MagicMock(id=1, image_type="interior", is_primary=True, is_background_processed=False),
            MagicMock(id=2, image_type="cover", is_primary=False, is_background_processed=False),
        ]

        result = select_best_source_image(images, primary_image_id=1)
        assert result.id == 2

    def test_falls_back_to_primary_when_no_preferred_types(self):
        """Should fall back to primary image if no preferred types."""
        from handler import select_best_source_image

        images = [
            MagicMock(id=1, image_type=None, is_primary=True, is_background_processed=False),
            MagicMock(id=2, image_type="interior", is_primary=False, is_background_processed=False),
            MagicMock(id=3, image_type=None, is_primary=False, is_background_processed=False),
        ]

        result = select_best_source_image(images, primary_image_id=1)
        assert result.id == 1

    def test_falls_back_to_passed_image_id_when_all_null(self):
        """Should use passed image_id if no types and no primary flag."""
        from handler import select_best_source_image

        images = [
            MagicMock(id=1, image_type=None, is_primary=False, is_background_processed=False),
            MagicMock(id=2, image_type=None, is_primary=False, is_background_processed=False),
            MagicMock(id=3, image_type=None, is_primary=False, is_background_processed=False),
        ]

        result = select_best_source_image(images, primary_image_id=2)
        assert result.id == 2

    def test_skips_already_processed_images(self):
        """Should not select images that are already background processed."""
        from handler import select_best_source_image

        images = [
            MagicMock(
                id=1, image_type="title_page", is_primary=False, is_background_processed=True
            ),
            MagicMock(id=2, image_type="binding", is_primary=False, is_background_processed=False),
            MagicMock(id=3, image_type=None, is_primary=True, is_background_processed=False),
        ]

        result = select_best_source_image(images, primary_image_id=3)
        assert result.id == 2  # Skips processed title_page, picks binding
