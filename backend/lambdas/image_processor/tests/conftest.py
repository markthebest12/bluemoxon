"""Pytest fixtures for image processor Lambda tests."""

import json
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

# Add the lambda directory to sys.path so we can import handler directly
lambda_dir = Path(__file__).parent.parent
if str(lambda_dir) not in sys.path:
    sys.path.insert(0, str(lambda_dir))

# Mock rembg before importing handler (it's only available in the Lambda container)
mock_rembg = ModuleType("rembg")
mock_rembg.new_session = MagicMock(return_value=MagicMock())
mock_rembg.remove = MagicMock(return_value=b"mock-processed-image")
sys.modules["rembg"] = mock_rembg


@pytest.fixture
def mock_db_session():
    """Mock SQLAlchemy database session."""
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.query.return_value.filter.return_value.scalar.return_value = 0
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    session.flush = MagicMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_s3_client():
    """Mock boto3 S3 client."""
    client = MagicMock()
    client.get_object.return_value = {
        "Body": MagicMock(read=MagicMock(return_value=b"fake-image-bytes"))
    }
    client.put_object.return_value = {}
    return client


@pytest.fixture
def mock_book_image():
    """Mock BookImage model instance."""
    image = MagicMock()
    image.id = 789
    image.book_id = 123
    image.s3_key = "books/123/original.jpg"
    image.cloudfront_url = "https://cdn.example.com/books/123/original.jpg"
    image.display_order = 0
    image.is_primary = True
    image.is_background_processed = False
    return image


@pytest.fixture
def mock_processing_job():
    """Mock ImageProcessingJob model instance."""
    job = MagicMock()
    job.id = "job-456"
    job.book_id = 123
    job.source_image_id = 789
    job.status = "pending"
    job.attempt_count = 0
    job.model_used = None
    job.processed_image_id = None
    job.failure_reason = None
    job.completed_at = None
    return job


@pytest.fixture
def sqs_event():
    """Sample SQS event with a single record."""
    return {
        "Records": [
            {
                "messageId": "msg-123",
                "body": json.dumps(
                    {
                        "job_id": "job-456",
                        "book_id": 123,
                        "image_id": 789,
                    }
                ),
            }
        ]
    }


@pytest.fixture
def sqs_event_multiple():
    """Sample SQS event with multiple records."""
    return {
        "Records": [
            {
                "messageId": "msg-1",
                "body": json.dumps(
                    {
                        "job_id": "job-1",
                        "book_id": 100,
                        "image_id": 1000,
                    }
                ),
            },
            {
                "messageId": "msg-2",
                "body": json.dumps(
                    {
                        "job_id": "job-2",
                        "book_id": 200,
                        "image_id": 2000,
                    }
                ),
            },
        ]
    }


@pytest.fixture
def smoke_test_event():
    """Smoke test event."""
    return {"smoke_test": True}


@pytest.fixture
def mock_environment(monkeypatch):
    """Set up environment variables for testing."""
    monkeypatch.setenv(
        "DATABASE_SECRET_ARN", "arn:aws:secretsmanager:us-east-1:123456789:secret:test"
    )
    monkeypatch.setenv("IMAGES_BUCKET", "test-images-bucket")
    monkeypatch.setenv("IMAGES_CDN_DOMAIN", "cdn.test.example.com")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    yield
