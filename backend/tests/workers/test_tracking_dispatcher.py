"""Tests for tracking dispatcher Lambda handler."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.models import Book
from app.workers.tracking_dispatcher import dispatch_tracking_jobs, handler


@pytest.fixture
def sample_books(db):
    """Create sample books for testing."""
    # Active book with tracking number
    book1 = Book(
        title="Book 1",
        tracking_active=True,
        tracking_number="1Z123456789",
        tracking_carrier="UPS",
    )
    db.add(book1)

    # Active book with tracking number
    book2 = Book(
        title="Book 2",
        tracking_active=True,
        tracking_number="1Z987654321",
        tracking_carrier="FedEx",
    )
    db.add(book2)

    # Active but no tracking number (should be skipped)
    book3 = Book(
        title="Book 3",
        tracking_active=True,
        tracking_number=None,
        tracking_carrier=None,
    )
    db.add(book3)

    # Inactive with tracking number (should be skipped)
    book4 = Book(
        title="Book 4",
        tracking_active=False,
        tracking_number="1Z555555555",
        tracking_carrier="UPS",
    )
    db.add(book4)

    db.commit()
    return [book1, book2, book3, book4]


def test_dispatch_tracking_jobs_sends_message_per_active_book(db, sample_books):
    """Test that dispatch_tracking_jobs sends one SQS message per active book."""
    mock_sqs = MagicMock()

    with patch("app.workers.tracking_dispatcher.get_sqs_client", return_value=mock_sqs):
        result = dispatch_tracking_jobs(db, "https://sqs.us-east-1.amazonaws.com/123/queue")

    assert result["dispatched"] == 2
    assert mock_sqs.send_message.call_count == 2

    # Verify message bodies contain correct book IDs
    calls = mock_sqs.send_message.call_args_list
    sent_book_ids = []
    for call in calls:
        body = json.loads(call[1]["MessageBody"])
        sent_book_ids.append(body["book_id"])

    assert sample_books[0].id in sent_book_ids
    assert sample_books[1].id in sent_book_ids


def test_dispatch_tracking_jobs_skips_books_without_tracking_number(db, sample_books):
    """Test that dispatch_tracking_jobs skips books without tracking numbers."""
    mock_sqs = MagicMock()

    with patch("app.workers.tracking_dispatcher.get_sqs_client", return_value=mock_sqs):
        result = dispatch_tracking_jobs(db, "https://sqs.us-east-1.amazonaws.com/123/queue")

    # Should only dispatch book1 and book2 (active with tracking numbers)
    assert result["dispatched"] == 2


def test_dispatch_tracking_jobs_skips_inactive_books(db, sample_books):
    """Test that dispatch_tracking_jobs skips inactive books."""
    mock_sqs = MagicMock()

    with patch("app.workers.tracking_dispatcher.get_sqs_client", return_value=mock_sqs):
        result = dispatch_tracking_jobs(db, "https://sqs.us-east-1.amazonaws.com/123/queue")

    # Should only dispatch book1 and book2 (active tracking_active=True)
    assert result["dispatched"] == 2


def test_dispatch_tracking_jobs_no_books(db):
    """Test dispatch_tracking_jobs when no active books exist."""
    mock_sqs = MagicMock()

    with patch("app.workers.tracking_dispatcher.get_sqs_client", return_value=mock_sqs):
        result = dispatch_tracking_jobs(db, "https://sqs.us-east-1.amazonaws.com/123/queue")

    assert result["dispatched"] == 0
    mock_sqs.send_message.assert_not_called()


def test_handler_raises_error_without_queue_url():
    """Test that handler raises ValueError when TRACKING_QUEUE_URL not set."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="TRACKING_QUEUE_URL"):
            handler({}, None)


def test_handler_dispatches_jobs(db, sample_books, monkeypatch):
    """Test that handler calls dispatch_tracking_jobs correctly."""
    mock_sqs = MagicMock()
    monkeypatch.setenv("TRACKING_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123/queue")

    with patch("app.workers.tracking_dispatcher.get_sqs_client", return_value=mock_sqs):
        with patch("app.workers.tracking_dispatcher.SessionLocal", return_value=db):
            result = handler({}, None)

    assert result["dispatched"] == 2
    assert mock_sqs.send_message.call_count == 2


def test_dispatch_message_format(db, sample_books):
    """Test that dispatch messages have correct format."""
    mock_sqs = MagicMock()

    with patch("app.workers.tracking_dispatcher.get_sqs_client", return_value=mock_sqs):
        dispatch_tracking_jobs(db, "https://sqs.us-east-1.amazonaws.com/123/queue")

    # Verify message structure
    call_args = mock_sqs.send_message.call_args_list
    for call in call_args:
        assert "QueueUrl" in call[1]
        assert "MessageBody" in call[1]

        body = json.loads(call[1]["MessageBody"])
        assert "book_id" in body
        assert isinstance(body["book_id"], int)
