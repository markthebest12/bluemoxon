"""Base interface for carrier tracking clients."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class TrackingStatus(StrEnum):
    """Standard tracking status values.

    All carrier implementations should normalize their status to these values.
    """

    IN_TRANSIT = "In Transit"
    OUT_FOR_DELIVERY = "Out for Delivery"
    DELIVERED = "Delivered"
    EXCEPTION = "Exception"
    PENDING = "Pending"
    UNKNOWN = "Unknown"


@dataclass
class TrackingResult:
    """Result of a tracking lookup.

    Attributes:
        status: Current status (e.g., "In Transit", "Delivered", "Exception")
        status_detail: Optional additional status information
        estimated_delivery: Expected delivery date if available
        delivered_at: Actual delivery timestamp if delivered
        location: Current location of package if available
        error: Error message if the lookup failed
    """

    status: str
    status_detail: str | None = None
    estimated_delivery: date | None = None
    delivered_at: datetime | None = None
    location: str | None = None
    error: str | None = None


class CarrierClient(ABC):
    """Abstract base class for carrier tracking clients.

    Each carrier implementation must:
    1. Set the `name` class attribute
    2. Implement `fetch_tracking()` to retrieve status from carrier API
    3. Implement `can_handle()` to check if a tracking number matches the carrier's pattern
    """

    name: str

    @abstractmethod
    def fetch_tracking(self, tracking_number: str) -> TrackingResult:
        """Fetch tracking information for a package.

        Args:
            tracking_number: The tracking number to look up

        Returns:
            TrackingResult with current status and delivery information
        """
        pass

    @classmethod
    @abstractmethod
    def can_handle(cls, tracking_number: str) -> bool:
        """Check if this carrier can handle the given tracking number.

        Args:
            tracking_number: The tracking number to check

        Returns:
            True if this carrier's pattern matches the tracking number
        """
        pass
