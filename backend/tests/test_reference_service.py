"""Tests for reference data services."""

from app.services.reference import get_or_create_binder, normalize_binder_name


class TestNormalizeBinderName:
    """Test binder name normalization and tier assignment."""

    def test_tier_1_sangorski(self):
        name, tier = normalize_binder_name("Sangorski & Sutcliffe")
        assert name == "Sangorski & Sutcliffe"
        assert tier == "TIER_1"

    def test_tier_1_sangorski_short(self):
        name, tier = normalize_binder_name("Sangorski")
        assert name == "Sangorski & Sutcliffe"
        assert tier == "TIER_1"

    def test_tier_1_riviere(self):
        name, tier = normalize_binder_name("Rivière & Son")
        assert name == "Rivière & Son"
        assert tier == "TIER_1"

    def test_tier_1_riviere_without_accent(self):
        name, tier = normalize_binder_name("Riviere")
        assert name == "Rivière & Son"
        assert tier == "TIER_1"

    def test_tier_1_zaehnsdorf(self):
        name, tier = normalize_binder_name("Zaehnsdorf")
        assert name == "Zaehnsdorf"
        assert tier == "TIER_1"

    def test_tier_1_cobden_sanderson(self):
        name, tier = normalize_binder_name("Cobden-Sanderson")
        assert name == "Cobden-Sanderson"
        assert tier == "TIER_1"

    def test_tier_1_doves_bindery(self):
        name, tier = normalize_binder_name("Doves Bindery")
        assert name == "Cobden-Sanderson"
        assert tier == "TIER_1"

    def test_tier_1_bedford(self):
        name, tier = normalize_binder_name("Bedford")
        assert name == "Bedford"
        assert tier == "TIER_1"

    def test_tier_2_morrell(self):
        name, tier = normalize_binder_name("Morrell")
        assert name == "Morrell"
        assert tier == "TIER_2"

    def test_tier_2_root(self):
        name, tier = normalize_binder_name("Root")
        assert name == "Root & Son"
        assert tier == "TIER_2"

    def test_tier_1_bayntun(self):
        """Bayntun is TIER_1 - prestigious Bath bindery, still operating."""
        name, tier = normalize_binder_name("Bayntun")
        assert name == "Bayntun"
        assert tier == "TIER_1"

    def test_tier_2_tout(self):
        name, tier = normalize_binder_name("Tout")
        assert name == "Tout"
        assert tier == "TIER_2"

    def test_tier_2_stikeman(self):
        name, tier = normalize_binder_name("Stikeman")
        assert name == "Stikeman"
        assert tier == "TIER_2"

    def test_unknown_binder_returns_none(self):
        """Unknown/Unidentified variants should return None to prevent proliferation."""
        name, tier = normalize_binder_name("Unknown Bindery")
        assert name is None
        assert tier is None

    def test_unidentified_variants_return_none(self):
        """All Unidentified variants with descriptions should return None."""
        variants = [
            "Unidentified",
            "UNIDENTIFIED",
            "Unidentified (no signature visible)",
            "Unidentified (Publisher's Binding)",
            "Unknown",
            "UNKNOWN",
            "Unknown (commercial trade binding)",
            "None",
            "none",
        ]
        for variant in variants:
            name, tier = normalize_binder_name(variant)
            assert name is None, f"Expected None for '{variant}', got '{name}'"
            assert tier is None

    def test_actual_binder_not_filtered(self):
        """Actual binder names should not be filtered."""
        name, tier = normalize_binder_name("Smith & Sons")
        assert name == "Smith & Sons"
        assert tier is None

    def test_case_insensitive(self):
        name, tier = normalize_binder_name("ZAEHNSDORF")
        assert name == "Zaehnsdorf"
        assert tier == "TIER_1"

    def test_no_false_positive_bedford_books_ltd(self):
        """Bedford Books Ltd should NOT match Bedford TIER_1.

        Regression test for issue #826: bidirectional substring matching
        caused 'Bedford' to match any name containing 'Bedford'.
        """
        name, tier = normalize_binder_name("Bedford Books Ltd")
        # Should NOT match Bedford (TIER_1) - this is a different company
        assert name == "Bedford Books Ltd"
        assert tier is None

    def test_no_false_positive_single_letter(self):
        """Single letter 'J' should NOT match 'J. Leighton' TIER_1.

        Regression test for issue #826: bidirectional substring matching
        caused short inputs to match long variants.
        """
        name, tier = normalize_binder_name("J")
        # Should NOT match J. Leighton (TIER_1) - catastrophic false positive
        assert name == "J"
        assert tier is None

    def test_no_false_positive_partial_name(self):
        """'Root Beer Company' should NOT match 'Root & Son' TIER_2.

        Regression test for issue #826: ensure substring matching only works
        when the VARIANT is found in the INPUT, not vice versa.
        """
        name, tier = normalize_binder_name("Root Beer Company")
        # Should NOT match Root & Son (TIER_2)
        assert name == "Root Beer Company"
        assert tier is None


class TestGetOrCreateBinder:
    """Test binder lookup/creation from parsed analysis."""

    def test_returns_none_for_none_input(self, db):
        result = get_or_create_binder(db, None)
        assert result is None

    def test_returns_none_for_empty_dict(self, db):
        result = get_or_create_binder(db, {})
        assert result is None

    def test_returns_none_for_missing_name(self, db):
        result = get_or_create_binder(db, {"confidence": "HIGH"})
        assert result is None

    def test_creates_tier_1_binder(self, db):
        result = get_or_create_binder(db, {"name": "Zaehnsdorf"})
        assert result is not None
        assert result.name == "Zaehnsdorf"
        assert result.tier == "TIER_1"
        assert result.id is not None

    def test_creates_tier_2_binder(self, db):
        result = get_or_create_binder(db, {"name": "Morrell"})
        assert result is not None
        assert result.name == "Morrell"
        assert result.tier == "TIER_2"

    def test_creates_unknown_binder_no_tier(self, db):
        result = get_or_create_binder(db, {"name": "Local Bindery"})
        assert result is not None
        assert result.name == "Local Bindery"
        assert result.tier is None

    def test_returns_existing_binder(self, db):
        # Create first binder
        first = get_or_create_binder(db, {"name": "Zaehnsdorf"})
        db.flush()

        # Look up again
        second = get_or_create_binder(db, {"name": "Zaehnsdorf"})
        assert second.id == first.id

    def test_normalizes_variant_names(self, db):
        # Create with variant name
        first = get_or_create_binder(db, {"name": "Riviere"})
        db.flush()

        # Look up with canonical name
        second = get_or_create_binder(db, {"name": "Rivière & Son"})
        assert second.id == first.id
        assert second.name == "Rivière & Son"

    def test_updates_tier_if_missing(self, db):
        from app.models.binder import Binder

        # Create binder without tier manually
        binder = Binder(name="Zaehnsdorf", tier=None)
        db.add(binder)
        db.flush()

        # Get via service - should update tier
        result = get_or_create_binder(db, {"name": "Zaehnsdorf"})
        assert result.id == binder.id
        assert result.tier == "TIER_1"
