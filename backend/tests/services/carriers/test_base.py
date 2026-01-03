"""Tests for base carrier interface."""

from datetime import date, datetime

import pytest


class TestTrackingResult:
    """Test TrackingResult dataclass."""

    def test_minimal_creation_with_status_only(self):
        """TrackingResult can be created with just status."""
        from app.services.carriers.base import TrackingResult

        result = TrackingResult(status="In Transit")

        assert result.status == "In Transit"
        assert result.status_detail is None
        assert result.estimated_delivery is None
        assert result.delivered_at is None
        assert result.location is None
        assert result.error is None

    def test_full_creation_with_all_fields(self):
        """TrackingResult can be created with all fields."""
        from app.services.carriers.base import TrackingResult

        now = datetime.utcnow()
        delivery_date = date(2026, 1, 5)

        result = TrackingResult(
            status="Delivered",
            status_detail="Left at front door",
            estimated_delivery=delivery_date,
            delivered_at=now,
            location="New York, NY",
            error=None,
        )

        assert result.status == "Delivered"
        assert result.status_detail == "Left at front door"
        assert result.estimated_delivery == delivery_date
        assert result.delivered_at == now
        assert result.location == "New York, NY"
        assert result.error is None

    def test_error_result(self):
        """TrackingResult can represent an error state."""
        from app.services.carriers.base import TrackingResult

        result = TrackingResult(
            status="Unknown",
            error="API timeout",
        )

        assert result.status == "Unknown"
        assert result.error == "API timeout"


class TestCarrierClientInterface:
    """Test CarrierClient abstract base class."""

    def test_cannot_instantiate_directly(self):
        """CarrierClient cannot be instantiated directly."""
        from app.services.carriers.base import CarrierClient

        with pytest.raises(TypeError):
            CarrierClient()

    def test_subclass_must_implement_abstract_methods(self):
        """Subclass without abstract methods raises TypeError."""
        from app.services.carriers.base import CarrierClient

        # Missing both fetch_tracking and can_handle
        class IncompleteCarrier(CarrierClient):
            name = "Incomplete"

        with pytest.raises(TypeError):
            IncompleteCarrier()

    def test_subclass_with_all_abstract_methods_can_instantiate(self):
        """Subclass with all abstract methods can be instantiated."""
        from app.services.carriers.base import CarrierClient, TrackingResult

        class CompleteCarrier(CarrierClient):
            name = "Complete"

            def fetch_tracking(self, tracking_number: str) -> TrackingResult:
                return TrackingResult(status="In Transit")

            @classmethod
            def can_handle(cls, tracking_number: str) -> bool:
                return False

        carrier = CompleteCarrier()
        assert carrier.name == "Complete"

    def test_can_handle_is_classmethod(self):
        """can_handle can be called on class without instantiation."""
        from app.services.carriers.base import CarrierClient, TrackingResult

        class TestCarrier(CarrierClient):
            name = "Test"

            def fetch_tracking(self, tracking_number: str) -> TrackingResult:
                return TrackingResult(status="In Transit")

            @classmethod
            def can_handle(cls, tracking_number: str) -> bool:
                return tracking_number.startswith("TEST")

        # Can call on class without instance
        assert TestCarrier.can_handle("TEST12345") is True
        assert TestCarrier.can_handle("OTHER12345") is False
