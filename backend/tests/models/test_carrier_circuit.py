"""Tests for CarrierCircuit model."""

from datetime import UTC, datetime

from app.models.carrier_circuit import CarrierCircuit


class TestCarrierCircuit:
    def test_create_circuit_state(self, db):
        """Create a new carrier circuit state."""
        circuit = CarrierCircuit(carrier_name="UPS")
        db.add(circuit)
        db.commit()
        assert circuit.carrier_name == "UPS"
        assert circuit.failure_count == 0

    def test_update_failure_count(self, db):
        """Update failure count and last failure timestamp."""
        circuit = CarrierCircuit(carrier_name="USPS", failure_count=2)
        db.add(circuit)
        db.commit()
        circuit.failure_count = 3
        circuit.last_failure_at = datetime.now(UTC)
        db.commit()
        assert circuit.failure_count == 3
        assert circuit.last_failure_at is not None
