"""Tests for orders extraction API."""

import logging

import pytest
from fastapi.testclient import TestClient

from app.api.v1.orders import _reset_warning_state, get_conversion_rate
from app.main import app


@pytest.fixture
def unauthenticated_client():
    """Client WITHOUT auth overrides - for security tests."""
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_warnings():
    """Reset warning state before each test to ensure clean slate."""
    _reset_warning_state()
    yield
    _reset_warning_state()


class TestGetConversionRate:
    """Tests for currency conversion rate function (#861)."""

    def test_usd_returns_1_without_db_lookup(self, db):
        """USD should return 1.0 without hitting the database."""
        rate = get_conversion_rate("USD", db)
        assert rate == 1.0

    def test_fallback_rate_returns_expected_value(self, db):
        """Fallback rate should return the hardcoded value."""
        rate = get_conversion_rate("GBP", db)
        assert rate == 1.35  # Must match fallback_rates in orders.py

        rate = get_conversion_rate("EUR", db)
        assert rate == 1.17  # Must match fallback_rates in orders.py

    def test_fallback_rate_logs_warning_once(self, db, caplog):
        """Using fallback rate should log warning only once per currency."""
        with caplog.at_level(logging.WARNING):
            get_conversion_rate("GBP", db)
            get_conversion_rate("GBP", db)  # Second call
            get_conversion_rate("GBP", db)  # Third call

        # Should only have ONE warning for GBP despite 3 calls
        gbp_warnings = [r for r in caplog.records if "GBP" in r.message]
        assert len(gbp_warnings) == 1
        assert "fallback" in gbp_warnings[0].message.lower()

    def test_unknown_currency_logs_warning_once(self, db, caplog):
        """Unknown currency should log warning only once and return 1.0."""
        with caplog.at_level(logging.WARNING):
            rate1 = get_conversion_rate("XYZ", db)
            rate2 = get_conversion_rate("XYZ", db)  # Second call

        assert rate1 == 1.0
        assert rate2 == 1.0

        # Should only have ONE warning for XYZ despite 2 calls
        xyz_warnings = [r for r in caplog.records if "XYZ" in r.message]
        assert len(xyz_warnings) == 1


class TestOrdersEndpointsSecurity:
    """Security tests for orders endpoints (issue #808).

    The /orders/extract endpoint triggers Bedrock LLM calls and MUST
    require authentication to prevent DoS attacks (bill racking).
    """

    def test_extract_requires_auth(self, unauthenticated_client):
        """POST /orders/extract requires authentication."""
        response = unauthenticated_client.post(
            "/api/v1/orders/extract",
            json={"text": "Order #12345"},
        )
        assert response.status_code == 401, (
            f"Expected 401 Unauthorized, got {response.status_code}. "
            "Endpoint must require authentication (issue #808)"
        )
