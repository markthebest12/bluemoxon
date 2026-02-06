"""Tests verifying cost_explorer derives correctly from MODEL_REGISTRY."""

from app.services.bedrock import MODEL_REGISTRY
from app.services.cost_explorer import AWS_SERVICE_TO_MODEL, MODEL_USAGE_DESCRIPTIONS


class TestCostExplorerDerived:
    """Verify cost_explorer mappings are derived from the single registry."""

    def test_all_billing_names_are_mapped(self):
        """Every billing name in the registry should appear in AWS_SERVICE_TO_MODEL."""
        for entry in MODEL_REGISTRY:
            for billing_name in entry.aws_billing_names:
                assert billing_name in AWS_SERVICE_TO_MODEL, (
                    f"Billing name '{billing_name}' from '{entry.key}' missing in AWS_SERVICE_TO_MODEL"
                )

    def test_billing_name_maps_to_display_name(self):
        """Each billing name should map to the correct display name."""
        for entry in MODEL_REGISTRY:
            for billing_name in entry.aws_billing_names:
                assert AWS_SERVICE_TO_MODEL[billing_name] == entry.display_name

    def test_usage_descriptions_cover_all_models(self):
        """Every model in the registry should have a usage description."""
        for entry in MODEL_REGISTRY:
            assert entry.display_name in MODEL_USAGE_DESCRIPTIONS, (
                f"Display name '{entry.display_name}' missing from MODEL_USAGE_DESCRIPTIONS"
            )

    def test_usage_descriptions_match_registry(self):
        """Usage descriptions should match the registry's usage field."""
        for entry in MODEL_REGISTRY:
            assert MODEL_USAGE_DESCRIPTIONS[entry.display_name] == entry.usage

    def test_no_extra_billing_names(self):
        """AWS_SERVICE_TO_MODEL should not contain names absent from the registry."""
        registry_billing_names = set()
        for entry in MODEL_REGISTRY:
            registry_billing_names.update(entry.aws_billing_names)

        for billing_name in AWS_SERVICE_TO_MODEL:
            assert billing_name in registry_billing_names, (
                f"Extra billing name '{billing_name}' not in registry"
            )
