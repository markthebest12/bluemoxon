"""Tests for shared AI connection parser."""

from app.services.ai_connection_parser import parse_ai_connection


def test_parse_valid_connection():
    raw = {
        "source_type": "author",
        "source_id": 31,
        "target_type": "author",
        "target_id": 227,
        "relationship": "family",
        "sub_type": "MARRIAGE",
        "confidence": 0.95,
        "evidence": "Married in 1846",
    }
    result = parse_ai_connection(raw)
    assert result is not None
    # Canonical ordering: "author:227" < "author:31" by string comparison
    assert result.source_node_id == "author:227"
    assert result.target_node_id == "author:31"
    assert result.strength == 9  # int(0.95 * 10)
    assert result.relationship == "family"
    assert result.sub_type == "MARRIAGE"
    assert result.confidence == 0.95
    assert result.evidence == "Married in 1846"
    assert result.edge_id == "e:author:227:author:31:family"


def test_parse_missing_required_field_returns_none():
    raw = {"source_type": "author", "source_id": 31}  # missing target fields
    assert parse_ai_connection(raw) is None


def test_parse_missing_relationship_returns_none():
    raw = {
        "source_type": "author",
        "source_id": 31,
        "target_type": "author",
        "target_id": 227,
        # no relationship
        "confidence": 0.5,
    }
    assert parse_ai_connection(raw) is None


def test_parse_invalid_relationship_returns_none():
    raw = {
        "source_type": "author",
        "source_id": 31,
        "target_type": "author",
        "target_id": 227,
        "relationship": "invalid_type",
        "confidence": 0.5,
    }
    assert parse_ai_connection(raw) is None


def test_parse_book_derived_relationship_returns_none():
    """Book-derived types (publisher, shared_publisher, binder) should be rejected."""
    for rel in ("publisher", "shared_publisher", "binder"):
        raw = {
            "source_type": "author",
            "source_id": 31,
            "target_type": "author",
            "target_id": 227,
            "relationship": rel,
            "confidence": 0.5,
        }
        assert parse_ai_connection(raw) is None, f"{rel} should be rejected"


def test_canonical_ordering():
    """Lower node ID should always be source."""
    raw = {
        "source_type": "publisher",
        "source_id": 999,
        "target_type": "author",
        "target_id": 1,
        "relationship": "friendship",
        "confidence": 0.5,
    }
    result = parse_ai_connection(raw)
    assert result is not None
    assert result.source_node_id == "author:1"
    assert result.target_node_id == "publisher:999"
    assert result.edge_id == "e:author:1:publisher:999:friendship"


def test_canonical_ordering_already_sorted():
    """If already in order, don't swap."""
    raw = {
        "source_type": "author",
        "source_id": 1,
        "target_type": "publisher",
        "target_id": 999,
        "relationship": "collaboration",
        "confidence": 0.7,
    }
    result = parse_ai_connection(raw)
    assert result.source_node_id == "author:1"
    assert result.target_node_id == "publisher:999"


def test_confidence_default():
    """Missing confidence defaults to 0.5, strength=5."""
    raw = {
        "source_type": "author",
        "source_id": 1,
        "target_type": "author",
        "target_id": 2,
        "relationship": "influence",
    }
    result = parse_ai_connection(raw)
    assert result.confidence == 0.5
    assert result.strength == 5


def test_confidence_clamp_low():
    """Very low confidence should clamp strength to 2."""
    raw = {
        "source_type": "author",
        "source_id": 1,
        "target_type": "author",
        "target_id": 2,
        "relationship": "scandal",
        "confidence": 0.1,
    }
    result = parse_ai_connection(raw)
    assert result.strength == 2


def test_confidence_clamp_high():
    """Confidence 1.0 should clamp strength to 10."""
    raw = {
        "source_type": "author",
        "source_id": 1,
        "target_type": "author",
        "target_id": 2,
        "relationship": "scandal",
        "confidence": 1.0,
    }
    result = parse_ai_connection(raw)
    assert result.strength == 10


def test_parsed_ai_connection_is_frozen():
    """ParsedAIConnection should be immutable."""
    raw = {
        "source_type": "author",
        "source_id": 1,
        "target_type": "author",
        "target_id": 2,
        "relationship": "friendship",
        "confidence": 0.5,
    }
    result = parse_ai_connection(raw)
    import pytest

    with pytest.raises(AttributeError):
        result.strength = 99


def test_optional_fields_default_none():
    """sub_type and evidence default to None when absent."""
    raw = {
        "source_type": "author",
        "source_id": 1,
        "target_type": "author",
        "target_id": 2,
        "relationship": "friendship",
        "confidence": 0.8,
    }
    result = parse_ai_connection(raw)
    assert result.sub_type is None
    assert result.evidence is None


def test_source_id_zero_is_valid():
    """source_id=0 should not be rejected (falsy but valid)."""
    raw = {
        "source_type": "author",
        "source_id": 0,
        "target_type": "author",
        "target_id": 2,
        "relationship": "friendship",
        "confidence": 0.5,
    }
    result = parse_ai_connection(raw)
    assert result is not None
    assert result.source_node_id == "author:0"
