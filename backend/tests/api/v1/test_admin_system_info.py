"""Tests for admin system-info endpoint."""

from fastapi.testclient import TestClient


def test_get_system_info_returns_expected_structure(client: TestClient):
    """Test that system-info returns all expected sections."""
    response = client.get("/api/v1/admin/system-info")
    assert response.status_code == 200

    data = response.json()

    # Check top-level keys
    assert "is_cold_start" in data
    assert "timestamp" in data
    assert "system" in data
    assert "health" in data
    assert "models" in data
    assert "scoring_config" in data
    assert "entity_tiers" in data


def test_get_system_info_system_section(client: TestClient):
    """Test system section has version info."""
    response = client.get("/api/v1/admin/system-info")
    data = response.json()

    system = data["system"]
    assert "version" in system
    assert "environment" in system


def test_get_system_info_health_section(client: TestClient):
    """Test health section has expected checks."""
    response = client.get("/api/v1/admin/system-info")
    data = response.json()

    health = data["health"]
    assert "overall" in health
    assert "total_latency_ms" in health
    assert "checks" in health

    checks = health["checks"]
    assert "database" in checks
    assert "s3" in checks
    assert "cognito" in checks


def test_get_system_info_scoring_config(client: TestClient):
    """Test scoring config has all expected sections."""
    response = client.get("/api/v1/admin/system-info")
    data = response.json()

    config = data["scoring_config"]
    assert "quality_points" in config
    assert "strategic_points" in config
    assert "thresholds" in config
    assert "weights" in config
    assert "offer_discounts" in config

    # Verify specific values match constants
    assert config["quality_points"]["publisher_tier_1"] == 25
    assert config["weights"]["quality"] == 0.6


def test_get_system_info_entity_tiers(client: TestClient):
    """Test entity tiers section structure."""
    response = client.get("/api/v1/admin/system-info")
    data = response.json()

    tiers = data["entity_tiers"]
    assert "authors" in tiers
    assert "publishers" in tiers
    assert "binders" in tiers

    # All should be lists (may be empty if no tiered entities)
    assert isinstance(tiers["authors"], list)
    assert isinstance(tiers["publishers"], list)
    assert isinstance(tiers["binders"], list)


def test_get_system_info_models(client: TestClient):
    """Test models section has bedrock model IDs and usage descriptions."""
    response = client.get("/api/v1/admin/system-info")
    data = response.json()

    models = data["models"]
    assert "sonnet" in models
    assert "opus" in models
    assert "haiku" in models

    # Each model should have model_id and usage
    for model_name in ["sonnet", "opus", "haiku"]:
        assert "model_id" in models[model_name]
        assert "usage" in models[model_name]
        assert "claude" in models[model_name]["model_id"].lower()
