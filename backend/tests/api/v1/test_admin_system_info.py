"""Tests for admin system-info endpoint."""

from fastapi.testclient import TestClient

from app.constants.image_processing import (
    BRIGHTNESS_THRESHOLD,
    IMAGE_TYPE_PRIORITY,
    MAX_ATTEMPTS,
    MAX_IMAGE_DIMENSION,
    MIN_OUTPUT_DIMENSION,
    THUMBNAIL_MAX_SIZE,
    THUMBNAIL_QUALITY,
    U2NET_FALLBACK_ATTEMPT,
)


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
    assert "image_processing" in data


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
    assert config["quality_points"]["preferred_bonus"] == 10
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


def test_get_system_info_image_processing(client: TestClient):
    """Test image_processing section has all expected constants from shared module."""
    response = client.get("/api/v1/admin/system-info")
    data = response.json()

    image_processing = data["image_processing"]

    # Verify all expected keys are present
    assert "brightness_threshold" in image_processing
    assert "max_attempts" in image_processing
    assert "max_image_dimension" in image_processing
    assert "thumbnail_max_size" in image_processing
    assert "thumbnail_quality" in image_processing
    assert "u2net_fallback_attempt" in image_processing
    assert "min_output_dimension" in image_processing
    assert "image_type_priority" in image_processing

    # Verify values match the shared constants (single source of truth)
    assert image_processing["brightness_threshold"] == BRIGHTNESS_THRESHOLD
    assert image_processing["max_attempts"] == MAX_ATTEMPTS
    assert image_processing["max_image_dimension"] == MAX_IMAGE_DIMENSION
    assert image_processing["thumbnail_max_size"] == list(THUMBNAIL_MAX_SIZE)
    assert image_processing["thumbnail_quality"] == THUMBNAIL_QUALITY
    assert image_processing["u2net_fallback_attempt"] == U2NET_FALLBACK_ATTEMPT
    assert image_processing["min_output_dimension"] == MIN_OUTPUT_DIMENSION
    assert image_processing["image_type_priority"] == IMAGE_TYPE_PRIORITY
