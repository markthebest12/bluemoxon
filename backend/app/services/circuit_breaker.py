"""Circuit breaker for carrier APIs."""

import logging
from datetime import UTC, datetime, timedelta

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
        True if circuit is open (still within timeout), False otherwise
    """
    circuit = db.query(CarrierCircuit).get(carrier_name)
    if not circuit or not circuit.circuit_open_until:
        return False
    # Handle both naive and aware datetimes
    open_until = circuit.circuit_open_until
    if open_until.tzinfo is None:
        open_until = open_until.replace(tzinfo=UTC)
    return open_until > datetime.now(UTC)


def record_failure(db: Session, carrier_name: str) -> None:
    """Record a carrier API failure.

    Args:
        db: Database session
        carrier_name: Name of the carrier

    Opens the circuit if failure count reaches threshold.
    """
    circuit = db.query(CarrierCircuit).get(carrier_name)
    if not circuit:
        circuit = CarrierCircuit(carrier_name=carrier_name, failure_count=0)
        db.add(circuit)
    circuit.failure_count += 1
    circuit.last_failure_at = datetime.now(UTC)
    circuit.updated_at = datetime.now(UTC)
    if circuit.failure_count >= FAILURE_THRESHOLD:
        circuit.circuit_open_until = datetime.now(UTC) + timedelta(minutes=OPEN_DURATION_MINUTES)
        logger.warning(f"Circuit opened for {carrier_name} after {circuit.failure_count} failures")
    db.commit()


def record_success(db: Session, carrier_name: str) -> None:
    """Record a successful carrier API call.

    Resets failure count and closes circuit if open.

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
