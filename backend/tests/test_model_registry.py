"""Tests for the unified ModelRegistry in bedrock.py."""

from app.services.bedrock import (
    MODEL_DISPLAY_NAMES,
    MODEL_IDS,
    MODEL_REGISTRY,
    MODEL_USAGE,
    ModelEntry,
    get_model_id,
)


class TestModelEntry:
    """Tests for the ModelEntry dataclass."""

    def test_model_entry_is_frozen(self):
        """ModelEntry should be immutable."""
        entry = ModelEntry(
            key="test",
            model_id="test-id",
            display_name="Test",
            aws_billing_names=("Test Billing",),
            usage="Testing",
        )
        assert entry.key == "test"
        # Frozen dataclass should raise on mutation
        try:
            entry.key = "mutated"  # type: ignore[misc]
            raise AssertionError("Should have raised FrozenInstanceError")
        except AttributeError:
            pass

    def test_active_defaults_to_true(self):
        """Active flag should default to True."""
        entry = ModelEntry(
            key="test",
            model_id="id",
            display_name="Test",
            aws_billing_names=(),
            usage="Testing",
        )
        assert entry.active is True

    def test_legacy_entry_has_no_model_id(self):
        """Legacy models have model_id=None."""
        entry = ModelEntry(
            key="legacy",
            model_id=None,
            display_name="Legacy",
            aws_billing_names=("Some Billing Name",),
            usage="Retired",
            active=False,
        )
        assert entry.model_id is None
        assert entry.active is False


class TestModelRegistry:
    """Tests for the MODEL_REGISTRY tuple and derived lookups."""

    def test_registry_is_non_empty(self):
        """Registry should contain at least the three active models."""
        assert len(MODEL_REGISTRY) >= 3

    def test_active_models_have_model_ids(self):
        """Every active model must have a non-None model_id."""
        for entry in MODEL_REGISTRY:
            if entry.active:
                assert entry.model_id is not None, f"Active model '{entry.key}' has no model_id"

    def test_all_keys_are_unique(self):
        """No duplicate keys in the registry."""
        keys = [e.key for e in MODEL_REGISTRY]
        assert len(keys) == len(set(keys)), f"Duplicate keys: {keys}"

    def test_all_billing_names_are_unique(self):
        """No billing name should map to two different models."""
        seen: dict[str, str] = {}
        for entry in MODEL_REGISTRY:
            for name in entry.aws_billing_names:
                assert name not in seen, (
                    f"Billing name '{name}' used by both '{seen[name]}' and '{entry.key}'"
                )
                seen[name] = entry.key

    def test_active_models_include_sonnet_opus_haiku(self):
        """The three expected active models should be present."""
        active_keys = {e.key for e in MODEL_REGISTRY if e.active}
        assert "sonnet" in active_keys
        assert "opus" in active_keys
        assert "haiku" in active_keys


class TestDerivedLookups:
    """Tests for MODEL_IDS, MODEL_USAGE, MODEL_DISPLAY_NAMES."""

    def test_model_ids_only_active(self):
        """MODEL_IDS should only contain active models."""
        for key in MODEL_IDS:
            entry = next(e for e in MODEL_REGISTRY if e.key == key)
            assert entry.active, f"Inactive model '{key}' found in MODEL_IDS"

    def test_model_ids_match_registry(self):
        """MODEL_IDS values should match registry model_id fields."""
        for key, model_id in MODEL_IDS.items():
            entry = next(e for e in MODEL_REGISTRY if e.key == key)
            assert entry.model_id == model_id

    def test_model_usage_match_registry(self):
        """MODEL_USAGE values should match registry usage fields."""
        for key, usage in MODEL_USAGE.items():
            entry = next(e for e in MODEL_REGISTRY if e.key == key)
            assert entry.usage == usage

    def test_display_names_match_registry(self):
        """MODEL_DISPLAY_NAMES should match registry display_name fields."""
        for key, display_name in MODEL_DISPLAY_NAMES.items():
            entry = next(e for e in MODEL_REGISTRY if e.key == key)
            assert entry.display_name == display_name

    def test_display_names_contains_expected(self):
        """Display names should include all active models."""
        assert "sonnet" in MODEL_DISPLAY_NAMES
        assert "opus" in MODEL_DISPLAY_NAMES
        assert "haiku" in MODEL_DISPLAY_NAMES

    def test_get_model_id_returns_correct_id(self):
        """get_model_id should return the right Bedrock model ID."""
        assert get_model_id("sonnet") == MODEL_IDS["sonnet"]
        assert get_model_id("opus") == MODEL_IDS["opus"]
        assert get_model_id("haiku") == MODEL_IDS["haiku"]

    def test_get_model_id_falls_back_to_sonnet(self):
        """get_model_id with unknown name should fall back to sonnet."""
        assert get_model_id("nonexistent") == MODEL_IDS["sonnet"]
