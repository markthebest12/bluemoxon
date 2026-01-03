"""Tests for tracking worker Lambda handler."""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.models import Book, CarrierCircuit
from app.workers.tracking_worker import handler, process_tracking_job


@pytest.fixture
def sample_book(db):
    """Create a sample book with tracking info."""
    book = Book(
        title="Test Book",
        tracking_number="1Z123456789",
        tracking_carrier="UPS",
        tracking_status="In Transit",
    )
    db.add(book)
    db.commit()
    return book


def test_process_tracking_job_success(db, sample_book):
    """Test process_tracking_job updates status on successful tracking fetch."""
    mock_result = MagicMock()
    mock_result.status = "Delivered"

    mock_carrier = MagicMock()
    mock_carrier.fetch_tracking.return_value = mock_result

    with patch("app.workers.tracking_worker.get_carrier", return_value=mock_carrier):
        with patch("app.workers.tracking_worker.is_circuit_open", return_value=False):
            result = process_tracking_job(db, sample_book.id)

    assert result["success"] is True
    assert result["status"] == "Delivered"

    db.refresh(sample_book)
    assert sample_book.tracking_status == "Delivered"
    assert sample_book.tracking_last_checked is not None


def test_process_tracking_job_sets_delivered_at(db, sample_book):
    """Test that process_tracking_job sets tracking_delivered_at when status is Delivered."""
    assert sample_book.tracking_delivered_at is None

    mock_result = MagicMock()
    mock_result.status = "Delivered"

    mock_carrier = MagicMock()
    mock_carrier.fetch_tracking.return_value = mock_result

    with patch("app.workers.tracking_worker.get_carrier", return_value=mock_carrier):
        with patch("app.workers.tracking_worker.is_circuit_open", return_value=False):
            process_tracking_job(db, sample_book.id)

    db.refresh(sample_book)
    assert sample_book.tracking_delivered_at is not None


def test_process_tracking_job_does_not_overwrite_delivered_at(db, sample_book):
    """Test that process_tracking_job doesn't overwrite existing tracking_delivered_at."""
    # Set delivered_at to a specific time before calling the worker
    original_time = datetime(2025, 12, 1, 12, 0, 0)
    sample_book.tracking_delivered_at = original_time
    db.commit()
    original_id = sample_book.tracking_delivered_at

    mock_result = MagicMock()
    mock_result.status = "Delivered"

    mock_carrier = MagicMock()
    mock_carrier.fetch_tracking.return_value = mock_result

    with patch("app.workers.tracking_worker.get_carrier", return_value=mock_carrier):
        with patch("app.workers.tracking_worker.is_circuit_open", return_value=False):
            process_tracking_job(db, sample_book.id)

    db.refresh(sample_book)
    # Verify the time wasn't changed - should still be the original value
    assert sample_book.tracking_delivered_at == original_id


def test_process_tracking_job_book_not_found(db):
    """Test process_tracking_job returns error when book not found."""
    result = process_tracking_job(db, 99999)

    assert result["success"] is False
    assert result["error"] == "Book not found"


def test_process_tracking_job_no_carrier(db):
    """Test process_tracking_job returns error when book has no carrier."""
    book = Book(title="Test Book", tracking_carrier=None)
    db.add(book)
    db.commit()

    result = process_tracking_job(db, book.id)

    assert result["success"] is False
    assert result["error"] == "No carrier"


def test_process_tracking_job_circuit_open(db, sample_book):
    """Test process_tracking_job raises exception when circuit is open."""
    with patch("app.workers.tracking_worker.is_circuit_open", return_value=True):
        with pytest.raises(Exception, match="Circuit open"):
            process_tracking_job(db, sample_book.id)


def test_process_tracking_job_carrier_api_failure(db, sample_book):
    """Test process_tracking_job records failure and raises exception on carrier error."""
    mock_carrier = MagicMock()
    mock_carrier.fetch_tracking.side_effect = Exception("API Error")

    with patch("app.workers.tracking_worker.get_carrier", return_value=mock_carrier):
        with patch("app.workers.tracking_worker.is_circuit_open", return_value=False):
            with patch("app.workers.tracking_worker.record_failure") as mock_failure:
                with pytest.raises(Exception, match="API Error"):
                    process_tracking_job(db, sample_book.id)

                mock_failure.assert_called_once_with(db, "UPS")


def test_process_tracking_job_calls_record_success(db, sample_book):
    """Test process_tracking_job calls record_success on successful fetch."""
    mock_result = MagicMock()
    mock_result.status = "In Transit"

    mock_carrier = MagicMock()
    mock_carrier.fetch_tracking.return_value = mock_result

    with patch("app.workers.tracking_worker.get_carrier", return_value=mock_carrier):
        with patch("app.workers.tracking_worker.is_circuit_open", return_value=False):
            with patch("app.workers.tracking_worker.record_success") as mock_success:
                process_tracking_job(db, sample_book.id)

                mock_success.assert_called_once_with(db, "UPS")


def test_handler_processes_messages(db, sample_book):
    """Test handler processes SQS messages correctly."""
    mock_result = MagicMock()
    mock_result.status = "In Transit"

    mock_carrier = MagicMock()
    mock_carrier.fetch_tracking.return_value = mock_result

    event = {
        "Records": [
            {
                "messageId": "msg-123",
                "body": json.dumps({"book_id": sample_book.id}),
            }
        ]
    }

    with patch("app.workers.tracking_worker.get_carrier", return_value=mock_carrier):
        with patch("app.workers.tracking_worker.is_circuit_open", return_value=False):
            with patch("app.workers.tracking_worker.SessionLocal", return_value=db):
                result = handler(event, None)

    assert result["batchItemFailures"] == []


def test_handler_returns_failed_items(db, sample_book):
    """Test handler returns failed message IDs in batchItemFailures."""
    mock_result = MagicMock()
    mock_result.status = "In Transit"

    mock_carrier = MagicMock()
    mock_carrier.fetch_tracking.return_value = mock_result

    event = {
        "Records": [
            {
                "messageId": "msg-123",
                "body": json.dumps({"book_id": 99999}),
            }
        ]
    }

    with patch("app.workers.tracking_worker.get_carrier", return_value=mock_carrier):
        with patch("app.workers.tracking_worker.is_circuit_open", return_value=False):
            with patch("app.workers.tracking_worker.SessionLocal", return_value=db):
                result = handler(event, None)

    # Failed message should NOT be in batchItemFailures because process_tracking_job
    # returns early without raising exception for missing books
    assert result["batchItemFailures"] == []


def test_handler_returns_failed_items_on_exception(db, sample_book):
    """Test handler returns message ID on actual exception."""
    mock_carrier = MagicMock()
    mock_carrier.fetch_tracking.side_effect = Exception("API Error")

    event = {
        "Records": [
            {
                "messageId": "msg-failed",
                "body": json.dumps({"book_id": sample_book.id}),
            }
        ]
    }

    with patch("app.workers.tracking_worker.get_carrier", return_value=mock_carrier):
        with patch("app.workers.tracking_worker.is_circuit_open", return_value=False):
            with patch("app.workers.tracking_worker.SessionLocal", return_value=db):
                result = handler(event, None)

    assert result["batchItemFailures"] == [{"itemIdentifier": "msg-failed"}]


def test_handler_empty_records(db):
    """Test handler handles empty SQS records."""
    event = {"Records": []}

    with patch("app.workers.tracking_worker.SessionLocal", return_value=db):
        result = handler(event, None)

    assert result["batchItemFailures"] == []


def test_handler_multiple_messages(db):
    """Test handler processes multiple SQS messages."""
    book1 = Book(title="Book 1", tracking_number="1Z123", tracking_carrier="UPS")
    book2 = Book(title="Book 2", tracking_number="1Z456", tracking_carrier="UPS")
    db.add(book1)
    db.add(book2)
    db.commit()

    mock_result = MagicMock()
    mock_result.status = "In Transit"

    mock_carrier = MagicMock()
    mock_carrier.fetch_tracking.return_value = mock_result

    event = {
        "Records": [
            {
                "messageId": "msg-1",
                "body": json.dumps({"book_id": book1.id}),
            },
            {
                "messageId": "msg-2",
                "body": json.dumps({"book_id": book2.id}),
            },
        ]
    }

    with patch("app.workers.tracking_worker.get_carrier", return_value=mock_carrier):
        with patch("app.workers.tracking_worker.is_circuit_open", return_value=False):
            with patch("app.workers.tracking_worker.SessionLocal", return_value=db):
                result = handler(event, None)

    assert result["batchItemFailures"] == []
    assert mock_carrier.fetch_tracking.call_count == 2
