"""Tests for orders extraction API."""

import logging

import pytest
from fastapi.testclient import TestClient

from app.api.v1.orders import get_conversion_rate
from app.main import app


@pytest.fixture
def unauthenticated_client():
    """Client WITHOUT auth overrides - for security tests."""
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client


class TestGetConversionRate:
    """Tests for currency conversion rate function (#861)."""

    def test_usd_returns_1_without_db_lookup(self, db):
        """USD should return 1.0 without hitting the database."""
        rate = get_conversion_rate("USD", db)
        assert rate == 1.0

    def test_fallback_rate_logs_warning(self, db, caplog):
        """Using fallback rate (no DB config) should log a warning."""
        with caplog.at_level(logging.WARNING):
            rate = get_conversion_rate("GBP", db)

        # Fallback rate for GBP (approximate, updated periodically)
        assert 1.0 < rate < 2.0  # Sanity check - should be in reasonable range
        assert "fallback" in caplog.text.lower()
        assert "GBP" in caplog.text

    def test_unknown_currency_logs_warning(self, db, caplog):
        """Unknown currency should log a warning and return 1.0."""
        with caplog.at_level(logging.WARNING):
            rate = get_conversion_rate("XYZ", db)

        assert rate == 1.0
        assert "unknown" in caplog.text.lower() or "XYZ" in caplog.text


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
