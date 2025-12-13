"""Tests for reference data services."""

import pytest

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

    def test_tier_2_bayntun(self):
        name, tier = normalize_binder_name("Bayntun")
        assert name == "Bayntun"
        assert tier == "TIER_2"

    def test_tier_2_tout(self):
        name, tier = normalize_binder_name("Tout")
        assert name == "Tout"
        assert tier == "TIER_2"

    def test_tier_2_stikeman(self):
        name, tier = normalize_binder_name("Stikeman")
        assert name == "Stikeman"
        assert tier == "TIER_2"

    def test_unknown_binder_no_tier(self):
        name, tier = normalize_binder_name("Unknown Bindery")
        assert name == "Unknown Bindery"
        assert tier is None

    def test_case_insensitive(self):
        name, tier = normalize_binder_name("ZAEHNSDORF")
        assert name == "Zaehnsdorf"
        assert tier == "TIER_1"


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
        result = get_or_create_binder(db, {"name": "Bayntun"})
        assert result is not None
        assert result.name == "Bayntun"
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
