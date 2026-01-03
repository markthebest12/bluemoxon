"""Tests for circuit breaker service."""

from datetime import UTC, datetime, timedelta

from app.models.carrier_circuit import CarrierCircuit
from app.services.circuit_breaker import (
    FAILURE_THRESHOLD,
    OPEN_DURATION_MINUTES,
    is_circuit_open,
    record_failure,
    record_success,
)


class TestIsCircuitOpen:
    """Tests for is_circuit_open function."""

    def test_circuit_not_open_when_no_state(self, db):
        """Circuit is not open when carrier has no state."""
        assert is_circuit_open(db, "UPS") is False

    def test_circuit_not_open_when_no_open_until(self, db):
        """Circuit is not open when circuit_open_until is None."""
        circuit = CarrierCircuit(carrier_name="FEDEX", failure_count=5)
        db.add(circuit)
        db.commit()
        assert is_circuit_open(db, "FEDEX") is False

    def test_circuit_open_when_within_timeout(self, db):
        """Circuit is open when within timeout period."""
        open_until = datetime.now(UTC) + timedelta(minutes=10)
        circuit = CarrierCircuit(
            carrier_name="USPS",
            failure_count=3,
            circuit_open_until=open_until,
        )
        db.add(circuit)
        db.commit()
        assert is_circuit_open(db, "USPS") is True

    def test_circuit_not_open_when_timeout_expired(self, db):
        """Circuit is not open when timeout has expired."""
        open_until = datetime.now(UTC) - timedelta(minutes=1)
        circuit = CarrierCircuit(
            carrier_name="DHLS",
            failure_count=3,
            circuit_open_until=open_until,
        )
        db.add(circuit)
        db.commit()
        assert is_circuit_open(db, "DHLS") is False


class TestRecordFailure:
    """Tests for record_failure function."""

    def test_records_first_failure(self, db):
        """Records first failure for new carrier."""
        record_failure(db, "UPS")
        circuit = db.query(CarrierCircuit).get("UPS")
        assert circuit is not None
        assert circuit.failure_count == 1
        assert circuit.last_failure_at is not None
        assert circuit.circuit_open_until is None

    def test_increments_failure_count(self, db):
        """Increments failure count on subsequent failures."""
        circuit = CarrierCircuit(carrier_name="FEDEX", failure_count=1)
        db.add(circuit)
        db.commit()

        record_failure(db, "FEDEX")
        db.refresh(circuit)
        assert circuit.failure_count == 2
        assert circuit.circuit_open_until is None

    def test_opens_circuit_at_threshold(self, db):
        """Opens circuit when failure count reaches threshold."""
        circuit = CarrierCircuit(
            carrier_name="USPS",
            failure_count=FAILURE_THRESHOLD - 1,
        )
        db.add(circuit)
        db.commit()

        record_failure(db, "USPS")
        db.refresh(circuit)
        assert circuit.failure_count == FAILURE_THRESHOLD
        assert circuit.circuit_open_until is not None

    def test_circuit_open_until_correct_duration(self, db):
        """Sets circuit_open_until to correct duration from now."""
        before = datetime.now(UTC)
        record_failure(db, "DHL")
        circuit = db.query(CarrierCircuit).get("DHL")
        # Manually trigger threshold
        circuit.failure_count = FAILURE_THRESHOLD
        record_failure(db, "DHL")
        db.refresh(circuit)
        after = datetime.now(UTC)

        assert circuit.circuit_open_until is not None
        # Handle both naive and aware datetimes
        open_until = circuit.circuit_open_until
        if open_until.tzinfo is None:
            open_until = open_until.replace(tzinfo=UTC)
        expected_min = before + timedelta(minutes=OPEN_DURATION_MINUTES)
        expected_max = after + timedelta(minutes=OPEN_DURATION_MINUTES)
        assert expected_min <= open_until <= expected_max

    def test_updates_last_failure_at(self, db):
        """Updates last_failure_at timestamp on each failure."""
        circuit = CarrierCircuit(carrier_name="ONTRAC")
        db.add(circuit)
        db.commit()

        before = datetime.now(UTC)
        record_failure(db, "ONTRAC")
        db.refresh(circuit)
        after = datetime.now(UTC)

        assert circuit.last_failure_at is not None
        # Handle both naive and aware datetimes
        last_failure = circuit.last_failure_at
        if last_failure.tzinfo is None:
            last_failure = last_failure.replace(tzinfo=UTC)
        assert before <= last_failure <= after

    def test_updates_updated_at(self, db):
        """Updates updated_at timestamp on each failure."""
        circuit = CarrierCircuit(carrier_name="LASERSHIP")
        db.add(circuit)
        db.commit()

        before = datetime.now(UTC)
        record_failure(db, "LASERSHIP")
        db.refresh(circuit)
        after = datetime.now(UTC)

        assert circuit.updated_at is not None
        # Handle both naive and aware datetimes
        updated_at = circuit.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)
        assert before <= updated_at <= after

    def test_continues_opening_circuit_after_threshold(self, db):
        """Circuit remains open as failures continue beyond threshold."""
        circuit = CarrierCircuit(
            carrier_name="AMAZON",
            failure_count=FAILURE_THRESHOLD,
            circuit_open_until=datetime.now(UTC) + timedelta(minutes=10),
        )
        db.add(circuit)
        db.commit()

        record_failure(db, "AMAZON")
        db.refresh(circuit)
        assert circuit.failure_count == FAILURE_THRESHOLD + 1
        assert circuit.circuit_open_until is not None


class TestRecordSuccess:
    """Tests for record_success function."""

    def test_resets_failure_count_to_zero(self, db):
        """Resets failure count to zero on success."""
        circuit = CarrierCircuit(carrier_name="UPS", failure_count=3)
        db.add(circuit)
        db.commit()

        record_success(db, "UPS")
        db.refresh(circuit)
        assert circuit.failure_count == 0

    def test_clears_circuit_open_until(self, db):
        """Clears circuit_open_until timestamp on success."""
        open_until = datetime.now(UTC) + timedelta(minutes=30)
        circuit = CarrierCircuit(
            carrier_name="FEDEX",
            failure_count=3,
            circuit_open_until=open_until,
        )
        db.add(circuit)
        db.commit()

        record_success(db, "FEDEX")
        db.refresh(circuit)
        assert circuit.circuit_open_until is None

    def test_resets_both_failure_count_and_open_until(self, db):
        """Resets both failure count and circuit_open_until on success."""
        open_until = datetime.now(UTC) + timedelta(minutes=30)
        circuit = CarrierCircuit(
            carrier_name="USPS",
            failure_count=3,
            circuit_open_until=open_until,
        )
        db.add(circuit)
        db.commit()

        record_success(db, "USPS")
        db.refresh(circuit)
        assert circuit.failure_count == 0
        assert circuit.circuit_open_until is None

    def test_noop_for_nonexistent_carrier(self, db):
        """Does nothing when carrier has no state."""
        record_success(db, "NONEXISTENT")
        circuit = db.query(CarrierCircuit).get("NONEXISTENT")
        assert circuit is None

    def test_updates_updated_at(self, db):
        """Updates updated_at timestamp on success."""
        circuit = CarrierCircuit(carrier_name="DHL", failure_count=2)
        db.add(circuit)
        db.commit()

        before = datetime.now(UTC)
        record_success(db, "DHL")
        db.refresh(circuit)
        after = datetime.now(UTC)

        assert circuit.updated_at is not None
        # Handle both naive and aware datetimes
        updated_at = circuit.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)
        assert before <= updated_at <= after


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker workflow."""

    def test_circuit_breaker_workflow(self, db):
        """Tests complete circuit breaker workflow: failures, open, recovery."""
        carrier = "INTEGRATION_TEST"

        assert is_circuit_open(db, carrier) is False

        record_failure(db, carrier)
        record_failure(db, carrier)
        assert is_circuit_open(db, carrier) is False

        record_failure(db, carrier)
        assert is_circuit_open(db, carrier) is True

        record_success(db, carrier)
        assert is_circuit_open(db, carrier) is False

        circuit = db.query(CarrierCircuit).get(carrier)
        assert circuit.failure_count == 0

    def test_multiple_carriers_independent_state(self, db):
        """Tests that multiple carriers maintain independent state."""
        for _ in range(FAILURE_THRESHOLD):
            record_failure(db, "CARRIER_A")

        for _ in range(1):
            record_failure(db, "CARRIER_B")

        assert is_circuit_open(db, "CARRIER_A") is True
        assert is_circuit_open(db, "CARRIER_B") is False

        record_success(db, "CARRIER_A")
        assert is_circuit_open(db, "CARRIER_A") is False
        assert is_circuit_open(db, "CARRIER_B") is False
