"""Tests for orders extraction API."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def unauthenticated_client():
    """Client WITHOUT auth overrides - for security tests."""
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client


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
