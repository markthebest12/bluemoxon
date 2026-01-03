# Tracking Worker Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Split tracking polling into dispatcher + SQS + worker architecture with circuit breaker and DB-level phone validation.

**Architecture:** EventBridge → Dispatcher Lambda (queries books, sends to SQS) → SQS Queue → Worker Lambda (fetches carrier API, updates DB). Circuit breaker tracks per-carrier failures in DB.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, boto3, PostgreSQL, Terraform, pytest

---

## Task 1: Database Migration - Phone CHECK Constraint

**Files:**
- Create: `backend/alembic/versions/x7890123abcd_phone_e164_constraint.py`

**Step 1: Write the migration**

```python
"""add_phone_e164_constraint

Add CHECK constraint for E.164 phone number format.

Revision ID: x7890123abcd
Revises: w6789012wxyz
Create Date: 2026-01-02
"""

from collections.abc import Sequence
from alembic import op

revision: str = "x7890123abcd"
down_revision: str | None = "w6789012wxyz"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add E.164 phone number CHECK constraint."""
    op.execute("""
        ALTER TABLE users
        ADD CONSTRAINT users_phone_number_e164
        CHECK (phone_number IS NULL OR phone_number ~ '^\\+[1-9]\\d{1,14}$')
    """)


def downgrade() -> None:
    """Remove E.164 phone number CHECK constraint."""
    op.execute("ALTER TABLE users DROP CONSTRAINT users_phone_number_e164")
```

**Step 2: Verify migration file syntax**

Run: `cd backend && poetry run python -c "import alembic.versions.x7890123abcd_phone_e164_constraint"`

Expected: No import errors

**Step 3: Commit**

```bash
git add backend/alembic/versions/x7890123abcd_phone_e164_constraint.py
git commit -m "feat: add E.164 phone number CHECK constraint migration"
```

---

## Task 2: Database Migration - Circuit Breaker Table

**Files:**
- Modify: `backend/alembic/versions/x7890123abcd_phone_e164_constraint.py` (add to same migration)

**Step 1: Update migration to include circuit breaker table**

Add to the `upgrade()` function:

```python
def upgrade() -> None:
    """Add E.164 constraint and circuit breaker table."""
    # Phone constraint
    op.execute("""
        ALTER TABLE users
        ADD CONSTRAINT users_phone_number_e164
        CHECK (phone_number IS NULL OR phone_number ~ '^\\+[1-9]\\d{1,14}$')
    """)

    # Circuit breaker table
    op.execute("""
        CREATE TABLE carrier_circuit_state (
            carrier_name VARCHAR(50) PRIMARY KEY,
            failure_count INTEGER NOT NULL DEFAULT 0,
            last_failure_at TIMESTAMP WITH TIME ZONE,
            circuit_open_until TIMESTAMP WITH TIME ZONE,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)


def downgrade() -> None:
    """Remove constraint and table."""
    op.execute("DROP TABLE carrier_circuit_state")
    op.execute("ALTER TABLE users DROP CONSTRAINT users_phone_number_e164")
```

**Step 2: Commit**

```bash
git add backend/alembic/versions/x7890123abcd_phone_e164_constraint.py
git commit -m "feat: add circuit breaker table to migration"
```

---

## Task 3: Circuit Breaker Model

**Files:**
- Create: `backend/app/models/carrier_circuit.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/tests/models/test_carrier_circuit.py`

**Step 1: Write the failing test**

```python
# backend/tests/models/test_carrier_circuit.py
"""Tests for CarrierCircuit model."""

import pytest
from datetime import datetime, UTC

from app.models.carrier_circuit import CarrierCircuit


class TestCarrierCircuit:
    """Tests for CarrierCircuit model."""

    def test_create_circuit_state(self, db):
        """Creates circuit state with defaults."""
        circuit = CarrierCircuit(carrier_name="UPS")
        db.add(circuit)
        db.commit()

        assert circuit.carrier_name == "UPS"
        assert circuit.failure_count == 0
        assert circuit.last_failure_at is None
        assert circuit.circuit_open_until is None

    def test_update_failure_count(self, db):
        """Updates failure count."""
        circuit = CarrierCircuit(carrier_name="USPS", failure_count=2)
        db.add(circuit)
        db.commit()

        circuit.failure_count = 3
        circuit.last_failure_at = datetime.now(UTC)
        db.commit()

        assert circuit.failure_count == 3
        assert circuit.last_failure_at is not None
```

**Step 2: Run test to verify it fails**

Run: `cd backend && poetry run pytest tests/models/test_carrier_circuit.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'app.models.carrier_circuit'"

**Step 3: Write the model**

```python
# backend/app/models/carrier_circuit.py
"""Circuit breaker state for carrier APIs."""

from datetime import datetime
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CarrierCircuit(Base):
    """Tracks circuit breaker state per carrier.

    Used to prevent hammering failed carrier APIs.
    """

    __tablename__ = "carrier_circuit_state"

    carrier_name: Mapped[str] = mapped_column(String(50), primary_key=True)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    circuit_open_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

**Step 4: Add to models/__init__.py**

```python
# Add to backend/app/models/__init__.py
from app.models.carrier_circuit import CarrierCircuit
```

**Step 5: Run test to verify it passes**

Run: `cd backend && poetry run pytest tests/models/test_carrier_circuit.py -v`

Expected: PASS

**Step 6: Commit**

```bash
git add backend/app/models/carrier_circuit.py backend/app/models/__init__.py backend/tests/models/test_carrier_circuit.py
git commit -m "feat: add CarrierCircuit model"
```

---

## Task 4: Circuit Breaker Service

**Files:**
- Create: `backend/app/services/circuit_breaker.py`
- Create: `backend/tests/services/test_circuit_breaker.py`

**Step 1: Write the failing tests**

```python
# backend/tests/services/test_circuit_breaker.py
"""Tests for circuit breaker service."""

import pytest
from datetime import datetime, timedelta, UTC

from app.models.carrier_circuit import CarrierCircuit
from app.services.circuit_breaker import (
    is_circuit_open,
    record_failure,
    record_success,
    FAILURE_THRESHOLD,
    OPEN_DURATION_MINUTES,
)


class TestIsCircuitOpen:
    """Tests for is_circuit_open function."""

    def test_returns_false_when_no_state(self, db):
        """Returns False when no circuit state exists."""
        assert is_circuit_open(db, "UPS") is False

    def test_returns_false_when_circuit_not_open(self, db):
        """Returns False when circuit_open_until is None."""
        circuit = CarrierCircuit(carrier_name="UPS", failure_count=1)
        db.add(circuit)
        db.commit()

        assert is_circuit_open(db, "UPS") is False

    def test_returns_true_when_circuit_open(self, db):
        """Returns True when circuit_open_until is in the future."""
        circuit = CarrierCircuit(
            carrier_name="USPS",
            failure_count=3,
            circuit_open_until=datetime.now(UTC) + timedelta(minutes=10),
        )
        db.add(circuit)
        db.commit()

        assert is_circuit_open(db, "USPS") is True

    def test_returns_false_when_circuit_expired(self, db):
        """Returns False when circuit_open_until is in the past."""
        circuit = CarrierCircuit(
            carrier_name="DHL",
            failure_count=3,
            circuit_open_until=datetime.now(UTC) - timedelta(minutes=10),
        )
        db.add(circuit)
        db.commit()

        assert is_circuit_open(db, "DHL") is False


class TestRecordFailure:
    """Tests for record_failure function."""

    def test_creates_state_on_first_failure(self, db):
        """Creates circuit state on first failure."""
        record_failure(db, "UPS")

        circuit = db.query(CarrierCircuit).get("UPS")
        assert circuit is not None
        assert circuit.failure_count == 1
        assert circuit.last_failure_at is not None

    def test_increments_failure_count(self, db):
        """Increments failure count on subsequent failures."""
        circuit = CarrierCircuit(carrier_name="USPS", failure_count=1)
        db.add(circuit)
        db.commit()

        record_failure(db, "USPS")

        db.refresh(circuit)
        assert circuit.failure_count == 2

    def test_opens_circuit_at_threshold(self, db):
        """Opens circuit when failure count reaches threshold."""
        circuit = CarrierCircuit(
            carrier_name="DHL",
            failure_count=FAILURE_THRESHOLD - 1,
        )
        db.add(circuit)
        db.commit()

        record_failure(db, "DHL")

        db.refresh(circuit)
        assert circuit.failure_count == FAILURE_THRESHOLD
        assert circuit.circuit_open_until is not None
        assert circuit.circuit_open_until > datetime.now(UTC)


class TestRecordSuccess:
    """Tests for record_success function."""

    def test_resets_failure_count(self, db):
        """Resets failure count to zero on success."""
        circuit = CarrierCircuit(
            carrier_name="UPS",
            failure_count=2,
            last_failure_at=datetime.now(UTC),
        )
        db.add(circuit)
        db.commit()

        record_success(db, "UPS")

        db.refresh(circuit)
        assert circuit.failure_count == 0

    def test_clears_circuit_open_until(self, db):
        """Clears circuit_open_until on success."""
        circuit = CarrierCircuit(
            carrier_name="USPS",
            failure_count=3,
            circuit_open_until=datetime.now(UTC) + timedelta(minutes=10),
        )
        db.add(circuit)
        db.commit()

        record_success(db, "USPS")

        db.refresh(circuit)
        assert circuit.circuit_open_until is None

    def test_noop_when_no_state(self, db):
        """Does nothing when no circuit state exists."""
        record_success(db, "UNKNOWN")
        # Should not raise
```

**Step 2: Run test to verify it fails**

Run: `cd backend && poetry run pytest tests/services/test_circuit_breaker.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.circuit_breaker'"

**Step 3: Write the implementation**

```python
# backend/app/services/circuit_breaker.py
"""Circuit breaker for carrier APIs.

Prevents hammering failing carrier APIs by tracking failures
and temporarily blocking calls to carriers that are down.
"""

import logging
from datetime import datetime, timedelta, UTC

from sqlalchemy.orm import Session

from app.models.carrier_circuit import CarrierCircuit

logger = logging.getLogger(__name__)

FAILURE_THRESHOLD = 3
OPEN_DURATION_MINUTES = 30


def is_circuit_open(db: Session, carrier_name: str) -> bool:
    """Check if circuit is open for a carrier.

    Args:
        db: Database session
        carrier_name: Name of the carrier

    Returns:
        True if circuit is open (should skip), False otherwise
    """
    circuit = db.query(CarrierCircuit).get(carrier_name)

    if not circuit or not circuit.circuit_open_until:
        return False

    return circuit.circuit_open_until > datetime.now(UTC)


def record_failure(db: Session, carrier_name: str) -> None:
    """Record a carrier API failure.

    Increments failure count and opens circuit if threshold reached.

    Args:
        db: Database session
        carrier_name: Name of the carrier
    """
    circuit = db.query(CarrierCircuit).get(carrier_name)

    if not circuit:
        circuit = CarrierCircuit(carrier_name=carrier_name)
        db.add(circuit)

    circuit.failure_count += 1
    circuit.last_failure_at = datetime.now(UTC)
    circuit.updated_at = datetime.now(UTC)

    if circuit.failure_count >= FAILURE_THRESHOLD:
        circuit.circuit_open_until = datetime.now(UTC) + timedelta(
            minutes=OPEN_DURATION_MINUTES
        )
        logger.warning(
            f"Circuit opened for {carrier_name} after {circuit.failure_count} failures"
        )

    db.commit()


def record_success(db: Session, carrier_name: str) -> None:
    """Record a successful carrier API call.

    Resets failure count and closes circuit.

    Args:
        db: Database session
        carrier_name: Name of the carrier
    """
    circuit = db.query(CarrierCircuit).get(carrier_name)

    if not circuit:
        return

    circuit.failure_count = 0
    circuit.circuit_open_until = None
    circuit.updated_at = datetime.now(UTC)
    db.commit()
```

**Step 4: Run test to verify it passes**

Run: `cd backend && poetry run pytest tests/services/test_circuit_breaker.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/circuit_breaker.py backend/tests/services/test_circuit_breaker.py
git commit -m "feat: add circuit breaker service"
```

---

## Task 5: Remove detect_and_get_carrier

**Files:**
- Modify: `backend/app/services/carriers/__init__.py`
- Modify: `backend/tests/services/carriers/test_registry.py` (if exists)

**Step 1: Remove the function**

Remove `detect_and_get_carrier` function and its export from `backend/app/services/carriers/__init__.py`.

**Step 2: Remove from __all__**

Update `__all__` to remove `"detect_and_get_carrier"`.

**Step 3: Run tests to check for breakage**

Run: `cd backend && poetry run pytest tests/services/carriers/ -v`

Expected: PASS (or update tests if they test detect_and_get_carrier)

**Step 4: Commit**

```bash
git add backend/app/services/carriers/__init__.py
git commit -m "refactor: remove detect_and_get_carrier (require explicit carrier)"
```

---

## Task 6: Tracking Dispatcher Lambda Handler

**Files:**
- Create: `backend/app/workers/__init__.py`
- Create: `backend/app/workers/tracking_dispatcher.py`
- Create: `backend/tests/workers/__init__.py`
- Create: `backend/tests/workers/test_tracking_dispatcher.py`

**Step 1: Write the failing tests**

```python
# backend/tests/workers/test_tracking_dispatcher.py
"""Tests for tracking dispatcher Lambda handler."""

import json
import pytest
from unittest.mock import MagicMock, patch

from app.models import Book, User
from app.workers.tracking_dispatcher import handler, dispatch_tracking_jobs


class TestDispatchTrackingJobs:
    """Tests for dispatch_tracking_jobs function."""

    def test_sends_message_per_active_book(self, db):
        """Sends one SQS message per active tracking book."""
        user = User(cognito_sub="test-sub", email="test@example.com")
        db.add(user)
        db.commit()

        book1 = Book(
            title="Book 1",
            tracking_number="1Z999AA10123456784",
            tracking_carrier="UPS",
            tracking_active=True,
            user_id=user.id,
        )
        book2 = Book(
            title="Book 2",
            tracking_number="9400111899223033",
            tracking_carrier="USPS",
            tracking_active=True,
            user_id=user.id,
        )
        book3 = Book(
            title="Book 3 - no tracking",
            tracking_active=False,
            user_id=user.id,
        )
        db.add_all([book1, book2, book3])
        db.commit()

        mock_sqs = MagicMock()

        with patch("app.workers.tracking_dispatcher.get_sqs_client", return_value=mock_sqs):
            result = dispatch_tracking_jobs(db, "https://queue-url")

        assert result["dispatched"] == 2
        assert mock_sqs.send_message.call_count == 2

    def test_skips_books_without_tracking_number(self, db):
        """Skips books that have tracking_active but no tracking_number."""
        user = User(cognito_sub="test-sub", email="test@example.com")
        db.add(user)
        db.commit()

        book = Book(
            title="Book without number",
            tracking_active=True,
            tracking_number=None,
            user_id=user.id,
        )
        db.add(book)
        db.commit()

        mock_sqs = MagicMock()

        with patch("app.workers.tracking_dispatcher.get_sqs_client", return_value=mock_sqs):
            result = dispatch_tracking_jobs(db, "https://queue-url")

        assert result["dispatched"] == 0
        mock_sqs.send_message.assert_not_called()


class TestHandler:
    """Tests for Lambda handler."""

    def test_returns_dispatch_count(self):
        """Handler returns dispatched count."""
        with patch("app.workers.tracking_dispatcher.SessionLocal") as mock_session:
            with patch("app.workers.tracking_dispatcher.dispatch_tracking_jobs") as mock_dispatch:
                mock_dispatch.return_value = {"dispatched": 5}

                result = handler({}, None)

                assert result == {"dispatched": 5}
```

**Step 2: Run test to verify it fails**

Run: `cd backend && poetry run pytest tests/workers/test_tracking_dispatcher.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'app.workers'"

**Step 3: Write the implementation**

```python
# backend/app/workers/__init__.py
"""Lambda worker handlers."""
```

```python
# backend/app/workers/tracking_dispatcher.py
"""Tracking dispatcher Lambda handler.

Triggered by EventBridge hourly. Queries all books with active tracking
and sends each book ID to SQS for the worker to process.
"""

import json
import logging
import os

import boto3
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Book

logger = logging.getLogger(__name__)


def get_sqs_client():
    """Get SQS client. Extracted for testing."""
    return boto3.client("sqs")


def dispatch_tracking_jobs(db: Session, queue_url: str) -> dict:
    """Query active tracking books and send to SQS.

    Args:
        db: Database session
        queue_url: SQS queue URL

    Returns:
        dict with dispatch stats
    """
    sqs = get_sqs_client()

    # Query books with active tracking
    books = (
        db.query(Book.id)
        .filter(
            Book.tracking_active == True,  # noqa: E712
            Book.tracking_number.isnot(None),
        )
        .all()
    )

    dispatched = 0
    for (book_id,) in books:
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps({"book_id": book_id}),
        )
        dispatched += 1

    logger.info(f"Dispatched {dispatched} tracking jobs to SQS")
    return {"dispatched": dispatched}


def handler(event: dict, context) -> dict:
    """Lambda handler for EventBridge trigger.

    Args:
        event: EventBridge event (ignored)
        context: Lambda context (ignored)

    Returns:
        dict with dispatch stats
    """
    queue_url = os.environ.get("TRACKING_QUEUE_URL")
    if not queue_url:
        raise ValueError("TRACKING_QUEUE_URL environment variable not set")

    db = SessionLocal()
    try:
        return dispatch_tracking_jobs(db, queue_url)
    finally:
        db.close()
```

**Step 4: Create test __init__.py**

```python
# backend/tests/workers/__init__.py
"""Tests for Lambda workers."""
```

**Step 5: Run test to verify it passes**

Run: `cd backend && poetry run pytest tests/workers/test_tracking_dispatcher.py -v`

Expected: PASS

**Step 6: Commit**

```bash
git add backend/app/workers/ backend/tests/workers/
git commit -m "feat: add tracking dispatcher Lambda handler"
```

---

## Task 7: Tracking Worker Lambda Handler

**Files:**
- Create: `backend/app/workers/tracking_worker.py`
- Create: `backend/tests/workers/test_tracking_worker.py`

**Step 1: Write the failing tests**

```python
# backend/tests/workers/test_tracking_worker.py
"""Tests for tracking worker Lambda handler."""

import json
import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import MagicMock, patch

from app.models import Book, User
from app.models.carrier_circuit import CarrierCircuit
from app.services.carriers import TrackingResult, TrackingStatus
from app.workers.tracking_worker import handler, process_tracking_job


class TestProcessTrackingJob:
    """Tests for process_tracking_job function."""

    def test_updates_book_status_on_success(self, db):
        """Updates book tracking status on successful carrier fetch."""
        user = User(cognito_sub="test-sub", email="test@example.com")
        db.add(user)
        db.commit()

        book = Book(
            title="Test Book",
            tracking_number="1Z999AA10123456784",
            tracking_carrier="UPS",
            tracking_active=True,
            tracking_status="Pending",
            user_id=user.id,
        )
        db.add(book)
        db.commit()

        mock_carrier = MagicMock()
        mock_carrier.fetch_tracking.return_value = TrackingResult(
            status=TrackingStatus.IN_TRANSIT,
            location="Memphis, TN",
        )

        with patch("app.workers.tracking_worker.get_carrier", return_value=mock_carrier):
            result = process_tracking_job(db, book.id)

        db.refresh(book)
        assert book.tracking_status == "In Transit"
        assert result["success"] is True

    def test_skips_when_circuit_open(self, db):
        """Raises exception when circuit is open for carrier."""
        user = User(cognito_sub="test-sub", email="test@example.com")
        db.add(user)
        db.commit()

        book = Book(
            title="Test Book",
            tracking_number="1Z999AA10123456784",
            tracking_carrier="UPS",
            tracking_active=True,
            user_id=user.id,
        )
        db.add(book)
        db.commit()

        # Open circuit for UPS
        circuit = CarrierCircuit(
            carrier_name="UPS",
            failure_count=3,
            circuit_open_until=datetime.now(UTC) + timedelta(minutes=10),
        )
        db.add(circuit)
        db.commit()

        with pytest.raises(Exception, match="Circuit open for UPS"):
            process_tracking_job(db, book.id)

    def test_records_failure_on_carrier_error(self, db):
        """Records failure when carrier API fails."""
        user = User(cognito_sub="test-sub", email="test@example.com")
        db.add(user)
        db.commit()

        book = Book(
            title="Test Book",
            tracking_number="1Z999AA10123456784",
            tracking_carrier="UPS",
            tracking_active=True,
            user_id=user.id,
        )
        db.add(book)
        db.commit()

        mock_carrier = MagicMock()
        mock_carrier.fetch_tracking.side_effect = Exception("API timeout")

        with patch("app.workers.tracking_worker.get_carrier", return_value=mock_carrier):
            with pytest.raises(Exception, match="API timeout"):
                process_tracking_job(db, book.id)

        # Check failure was recorded
        circuit = db.query(CarrierCircuit).get("UPS")
        assert circuit is not None
        assert circuit.failure_count == 1


class TestHandler:
    """Tests for Lambda handler."""

    def test_processes_sqs_records(self):
        """Handler processes each SQS record."""
        event = {
            "Records": [
                {"body": json.dumps({"book_id": 1})},
                {"body": json.dumps({"book_id": 2})},
            ]
        }

        with patch("app.workers.tracking_worker.SessionLocal"):
            with patch("app.workers.tracking_worker.process_tracking_job") as mock_process:
                mock_process.return_value = {"success": True}

                result = handler(event, None)

                assert mock_process.call_count == 2
```

**Step 2: Run test to verify it fails**

Run: `cd backend && poetry run pytest tests/workers/test_tracking_worker.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'app.workers.tracking_worker'"

**Step 3: Write the implementation**

```python
# backend/app/workers/tracking_worker.py
"""Tracking worker Lambda handler.

Triggered by SQS. Processes one book at a time - fetches tracking
status from carrier API and updates the database.
"""

import json
import logging
from datetime import datetime, UTC

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Book
from app.services.carriers import get_carrier, TrackingStatus
from app.services.circuit_breaker import is_circuit_open, record_failure, record_success

logger = logging.getLogger(__name__)


def process_tracking_job(db: Session, book_id: int) -> dict:
    """Process a single tracking job.

    Args:
        db: Database session
        book_id: ID of the book to check

    Returns:
        dict with processing result

    Raises:
        Exception: If circuit is open or carrier API fails
    """
    book = db.query(Book).filter(Book.id == book_id).first()

    if not book:
        logger.warning(f"Book {book_id} not found")
        return {"success": False, "error": "Book not found"}

    if not book.tracking_carrier:
        logger.warning(f"Book {book_id} has no tracking carrier")
        return {"success": False, "error": "No carrier"}

    # Check circuit breaker
    if is_circuit_open(db, book.tracking_carrier):
        raise Exception(f"Circuit open for {book.tracking_carrier}")

    try:
        carrier = get_carrier(book.tracking_carrier)
        result = carrier.fetch_tracking(book.tracking_number)

        # Update book status
        book.tracking_status = result.status
        book.tracking_last_checked = datetime.now(UTC)

        # Handle delivery
        if result.status == TrackingStatus.DELIVERED:
            if book.tracking_delivered_at is None:
                book.tracking_delivered_at = datetime.now(UTC)

        db.commit()
        record_success(db, book.tracking_carrier)

        logger.info(f"Book {book_id} tracking updated: {result.status}")
        return {"success": True, "status": result.status}

    except Exception as e:
        record_failure(db, book.tracking_carrier)
        logger.error(f"Failed to fetch tracking for book {book_id}: {e}")
        raise


def handler(event: dict, context) -> dict:
    """Lambda handler for SQS trigger.

    Args:
        event: SQS event with Records
        context: Lambda context

    Returns:
        dict with batch item failures for partial batch response
    """
    batch_item_failures = []

    for record in event.get("Records", []):
        try:
            body = json.loads(record["body"])
            book_id = body["book_id"]

            db = SessionLocal()
            try:
                process_tracking_job(db, book_id)
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Failed to process record: {e}")
            batch_item_failures.append({
                "itemIdentifier": record.get("messageId")
            })

    return {"batchItemFailures": batch_item_failures}
```

**Step 4: Run test to verify it passes**

Run: `cd backend && poetry run pytest tests/workers/test_tracking_worker.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/workers/tracking_worker.py backend/tests/workers/test_tracking_worker.py
git commit -m "feat: add tracking worker Lambda handler"
```

---

## Task 8: Remove EventBridge Routing from main.py

**Files:**
- Modify: `backend/app/main.py`

**Step 1: Remove the poll_tracking routing**

Remove lines 125-144 from `main.py` - the entire `handler` function that routes between HTTP and EventBridge.

Replace with:

```python
# Mangum handler for HTTP requests
handler = Mangum(app, lifespan="off")
```

**Step 2: Remove unused imports**

Remove:
```python
from app.services.tracking_poller import poll_all_active_tracking
```

**Step 3: Run tests to verify nothing breaks**

Run: `cd backend && poetry run pytest tests/ -v --tb=short -q`

Expected: All tests PASS

**Step 4: Commit**

```bash
git add backend/app/main.py
git commit -m "refactor: remove EventBridge routing from main.py (now in separate Lambda)"
```

---

## Task 9: Terraform Module - tracking-worker

**Files:**
- Create: `infra/terraform/modules/tracking-worker/main.tf`
- Create: `infra/terraform/modules/tracking-worker/variables.tf`
- Create: `infra/terraform/modules/tracking-worker/outputs.tf`
- Create: `infra/terraform/modules/tracking-worker/versions.tf`

**Step 1: Create versions.tf**

```hcl
# infra/terraform/modules/tracking-worker/versions.tf
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}
```

**Step 2: Create variables.tf**

```hcl
# infra/terraform/modules/tracking-worker/variables.tf
variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name (staging/production)"
  type        = string
}

variable "handler_dispatcher" {
  description = "Handler for dispatcher Lambda"
  type        = string
  default     = "app.workers.tracking_dispatcher.handler"
}

variable "handler_worker" {
  description = "Handler for worker Lambda"
  type        = string
  default     = "app.workers.tracking_worker.handler"
}

variable "runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.12"
}

variable "memory_size_dispatcher" {
  description = "Memory for dispatcher Lambda (MB)"
  type        = number
  default     = 256
}

variable "memory_size_worker" {
  description = "Memory for worker Lambda (MB)"
  type        = number
  default     = 512
}

variable "timeout_dispatcher" {
  description = "Timeout for dispatcher Lambda (seconds)"
  type        = number
  default     = 60
}

variable "timeout_worker" {
  description = "Timeout for worker Lambda (seconds)"
  type        = number
  default     = 60
}

variable "reserved_concurrency" {
  description = "Max concurrent worker executions"
  type        = number
  default     = 10
}

variable "package_path" {
  description = "Path to Lambda deployment package"
  type        = string
}

variable "source_code_hash" {
  description = "Hash of deployment package"
  type        = string
}

variable "subnet_ids" {
  description = "VPC subnet IDs"
  type        = list(string)
  default     = []
}

variable "security_group_ids" {
  description = "VPC security group IDs"
  type        = list(string)
  default     = []
}

variable "environment_variables" {
  description = "Environment variables for Lambdas"
  type        = map(string)
  default     = {}
}

variable "secrets_arns" {
  description = "ARNs of secrets to access"
  type        = list(string)
  default     = []
}

variable "log_retention_days" {
  description = "CloudWatch log retention"
  type        = number
  default     = 14
}

variable "schedule_expression" {
  description = "EventBridge schedule expression"
  type        = string
  default     = "rate(1 hour)"
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
```

**Step 3: Create main.tf**

```hcl
# infra/terraform/modules/tracking-worker/main.tf
# =============================================================================
# Tracking Worker Module
# =============================================================================
# Creates SQS queue + dispatcher + worker Lambdas for async tracking updates.
# EventBridge → Dispatcher → SQS → Worker
# =============================================================================

# -----------------------------------------------------------------------------
# SQS Dead Letter Queue
# -----------------------------------------------------------------------------

resource "aws_sqs_queue" "dlq" {
  name                      = "${var.name_prefix}-tracking-jobs-dlq"
  message_retention_seconds = 1209600 # 14 days

  tags = var.tags
}

# -----------------------------------------------------------------------------
# SQS Main Queue
# -----------------------------------------------------------------------------

resource "aws_sqs_queue" "jobs" {
  name                       = "${var.name_prefix}-tracking-jobs"
  visibility_timeout_seconds = var.timeout_worker * 2
  message_retention_seconds  = 345600 # 4 days
  receive_wait_time_seconds  = 20     # Long polling

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })

  tags = var.tags
}

# -----------------------------------------------------------------------------
# IAM Role - Dispatcher
# -----------------------------------------------------------------------------

resource "aws_iam_role" "dispatcher" {
  name = "${var.name_prefix}-tracking-dispatcher-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "dispatcher_basic" {
  role       = aws_iam_role.dispatcher.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "dispatcher_vpc" {
  count      = length(var.subnet_ids) > 0 ? 1 : 0
  role       = aws_iam_role.dispatcher.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy" "dispatcher_sqs" {
  name = "sqs-send"
  role = aws_iam_role.dispatcher.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["sqs:SendMessage"]
      Resource = aws_sqs_queue.jobs.arn
    }]
  })
}

resource "aws_iam_role_policy" "dispatcher_secrets" {
  count = length(var.secrets_arns) > 0 ? 1 : 0
  name  = "secrets-access"
  role  = aws_iam_role.dispatcher.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = var.secrets_arns
    }]
  })
}

# -----------------------------------------------------------------------------
# IAM Role - Worker
# -----------------------------------------------------------------------------

resource "aws_iam_role" "worker" {
  name = "${var.name_prefix}-tracking-worker-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "worker_basic" {
  role       = aws_iam_role.worker.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "worker_vpc" {
  count      = length(var.subnet_ids) > 0 ? 1 : 0
  role       = aws_iam_role.worker.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy" "worker_sqs" {
  name = "sqs-receive"
  role = aws_iam_role.worker.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes"
      ]
      Resource = aws_sqs_queue.jobs.arn
    }]
  })
}

resource "aws_iam_role_policy" "worker_secrets" {
  count = length(var.secrets_arns) > 0 ? 1 : 0
  name  = "secrets-access"
  role  = aws_iam_role.worker.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = var.secrets_arns
    }]
  })
}

# -----------------------------------------------------------------------------
# CloudWatch Log Groups
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "dispatcher" {
  name              = "/aws/lambda/${var.name_prefix}-tracking-dispatcher"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/aws/lambda/${var.name_prefix}-tracking-worker"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Lambda - Dispatcher
# -----------------------------------------------------------------------------

resource "aws_lambda_function" "dispatcher" {
  function_name = "${var.name_prefix}-tracking-dispatcher"
  role          = aws_iam_role.dispatcher.arn
  handler       = var.handler_dispatcher
  runtime       = var.runtime
  memory_size   = var.memory_size_dispatcher
  timeout       = var.timeout_dispatcher

  filename         = var.package_path
  source_code_hash = var.source_code_hash

  environment {
    variables = merge(
      { ENVIRONMENT = var.environment, TRACKING_QUEUE_URL = aws_sqs_queue.jobs.url },
      var.environment_variables
    )
  }

  dynamic "vpc_config" {
    for_each = length(var.subnet_ids) > 0 ? [1] : []
    content {
      subnet_ids         = var.subnet_ids
      security_group_ids = var.security_group_ids
    }
  }

  tags = var.tags

  depends_on = [aws_cloudwatch_log_group.dispatcher]

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }
}

# -----------------------------------------------------------------------------
# Lambda - Worker
# -----------------------------------------------------------------------------

resource "aws_lambda_function" "worker" {
  function_name = "${var.name_prefix}-tracking-worker"
  role          = aws_iam_role.worker.arn
  handler       = var.handler_worker
  runtime       = var.runtime
  memory_size   = var.memory_size_worker
  timeout       = var.timeout_worker

  filename         = var.package_path
  source_code_hash = var.source_code_hash

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = merge(
      { ENVIRONMENT = var.environment },
      var.environment_variables
    )
  }

  dynamic "vpc_config" {
    for_each = length(var.subnet_ids) > 0 ? [1] : []
    content {
      subnet_ids         = var.subnet_ids
      security_group_ids = var.security_group_ids
    }
  }

  tags = var.tags

  depends_on = [aws_cloudwatch_log_group.worker]

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }
}

# -----------------------------------------------------------------------------
# SQS Event Source Mapping
# -----------------------------------------------------------------------------

resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.jobs.arn
  function_name    = aws_lambda_function.worker.arn
  batch_size       = 1

  function_response_types = ["ReportBatchItemFailures"]
}

# -----------------------------------------------------------------------------
# EventBridge Schedule → Dispatcher
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_event_rule" "schedule" {
  name                = "${var.name_prefix}-tracking-schedule"
  description         = "Hourly tracking poll"
  schedule_expression = var.schedule_expression

  tags = var.tags
}

resource "aws_cloudwatch_event_target" "dispatcher" {
  rule      = aws_cloudwatch_event_rule.schedule.name
  target_id = "tracking-dispatcher"
  arn       = aws_lambda_function.dispatcher.arn
}

resource "aws_lambda_permission" "eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.dispatcher.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.schedule.arn
}
```

**Step 4: Create outputs.tf**

```hcl
# infra/terraform/modules/tracking-worker/outputs.tf
output "queue_url" {
  description = "SQS queue URL"
  value       = aws_sqs_queue.jobs.url
}

output "queue_arn" {
  description = "SQS queue ARN"
  value       = aws_sqs_queue.jobs.arn
}

output "dlq_url" {
  description = "DLQ URL"
  value       = aws_sqs_queue.dlq.url
}

output "dispatcher_function_name" {
  description = "Dispatcher Lambda function name"
  value       = aws_lambda_function.dispatcher.function_name
}

output "worker_function_name" {
  description = "Worker Lambda function name"
  value       = aws_lambda_function.worker.function_name
}
```

**Step 5: Validate Terraform**

Run: `cd infra/terraform && terraform fmt -recursive && terraform validate`

Expected: Success

**Step 6: Commit**

```bash
git add infra/terraform/modules/tracking-worker/
git commit -m "feat: add tracking-worker Terraform module"
```

---

## Task 10: Wire Up Terraform Module

**Files:**
- Modify: `infra/terraform/main.tf` or environment-specific file
- Modify: `infra/terraform/envs/staging.tfvars`
- Modify: `infra/terraform/envs/production.tfvars`

**Step 1: Add module call in main.tf**

Add the tracking-worker module call similar to analysis-worker.

**Step 2: Add variables to tfvars**

Add any required variables to staging and production tfvars.

**Step 3: Plan and verify**

Run: `cd infra/terraform && AWS_PROFILE=bmx-staging terraform plan -var-file=envs/staging.tfvars`

Expected: Shows new resources to create

**Step 4: Commit**

```bash
git add infra/terraform/
git commit -m "feat: wire up tracking-worker module in staging/production"
```

---

## Task 11: Update Deploy Workflow

**Files:**
- Modify: `.github/workflows/deploy.yml`
- Modify: `.github/workflows/deploy-staging.yml`

**Step 1: Add deployment steps for new Lambdas**

Add steps to deploy tracking-dispatcher and tracking-worker Lambdas.

**Step 2: Commit**

```bash
git add .github/workflows/
git commit -m "ci: add tracking-worker Lambda deployment"
```

---

## Task 12: Run Full Test Suite

**Step 1: Run all backend tests**

Run: `cd backend && poetry run pytest -v --tb=short`

Expected: All tests PASS

**Step 2: Run linting**

Run: `cd backend && poetry run ruff check . && poetry run ruff format --check .`

Expected: No issues

**Step 3: Final commit if needed**

```bash
git add -A
git commit -m "chore: final cleanup"
```

---

## Summary

| Task | Description |
|------|-------------|
| 1 | Migration - phone CHECK constraint |
| 2 | Migration - circuit breaker table |
| 3 | CarrierCircuit model |
| 4 | Circuit breaker service |
| 5 | Remove detect_and_get_carrier |
| 6 | Tracking dispatcher Lambda |
| 7 | Tracking worker Lambda |
| 8 | Remove EventBridge from main.py |
| 9 | Terraform tracking-worker module |
| 10 | Wire up Terraform module |
| 11 | Update deploy workflows |
| 12 | Full test suite verification |
