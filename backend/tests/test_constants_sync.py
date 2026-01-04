"""Test that frontend and backend constants stay in sync.

This prevents drift when constants need to be updated in both places.
"""

import re
from pathlib import Path

import pytest

from app.constants import DEFAULT_ANALYSIS_MODEL


class TestConstantsSync:
    """Verify frontend/backend constants match."""

    def test_default_analysis_model_matches_frontend(self):
        """Ensure backend DEFAULT_ANALYSIS_MODEL matches frontend config.ts."""
        frontend_config = Path(__file__).parent.parent.parent / "frontend/src/config.ts"

        if not frontend_config.exists():
            pytest.skip("Frontend config not found (running in CI without frontend)")

        content = frontend_config.read_text()

        # Extract: export const DEFAULT_ANALYSIS_MODEL: AnalysisModel = "opus";
        match = re.search(r'export const DEFAULT_ANALYSIS_MODEL.*?=\s*["\'](\w+)["\']', content)
        assert match, "DEFAULT_ANALYSIS_MODEL not found in frontend/src/config.ts"

        frontend_default = match.group(1)
        assert frontend_default == DEFAULT_ANALYSIS_MODEL, (
            f"Frontend/backend DEFAULT_ANALYSIS_MODEL mismatch: "
            f"frontend={frontend_default!r}, backend={DEFAULT_ANALYSIS_MODEL!r}"
        )

    def test_default_analysis_model_is_valid(self):
        """Ensure DEFAULT_ANALYSIS_MODEL is a valid model name."""
        valid_models = {"sonnet", "opus", "haiku"}
        assert DEFAULT_ANALYSIS_MODEL in valid_models, (
            f"DEFAULT_ANALYSIS_MODEL={DEFAULT_ANALYSIS_MODEL!r} not in valid models: {valid_models}"
        )
