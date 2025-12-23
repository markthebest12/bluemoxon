"""Tests for publisher validation service."""

import pytest

from app.services.publisher_validation import auto_correct_publisher_name


class TestAutoCorrectPublisherName:
    """Test auto-correction rules for publisher names."""

    def test_removes_new_york_suffix(self):
        result = auto_correct_publisher_name("Harper & Brothers, New York")
        assert result == "Harper & Brothers"

    def test_removes_london_suffix(self):
        result = auto_correct_publisher_name("Macmillan and Co., London")
        assert result == "Macmillan and Co."

    def test_removes_philadelphia_suffix(self):
        result = auto_correct_publisher_name("J.B. Lippincott Company, Philadelphia")
        assert result == "J.B. Lippincott Company"

    def test_removes_boston_suffix(self):
        result = auto_correct_publisher_name("D.C. Heath & Co., Boston")
        assert result == "D.C. Heath & Co."

    def test_removes_parenthetical_edition_info(self):
        result = auto_correct_publisher_name("D.C. Heath & Co. (Arden Shakespeare)")
        assert result == "D.C. Heath & Co."

    def test_removes_parenthetical_series_info(self):
        result = auto_correct_publisher_name("Oxford University Press (World's Classics)")
        assert result == "Oxford University Press"

    def test_handles_dual_publisher_keeps_first(self):
        result = auto_correct_publisher_name("Doubleday, Page & Company / Review of Reviews")
        assert result == "Doubleday, Page & Company"

    def test_handles_dual_publisher_with_ampersand(self):
        result = auto_correct_publisher_name("Henry Frowde / Oxford University Press")
        assert result == "Oxford University Press"

    def test_expands_d_to_david_for_bogue(self):
        result = auto_correct_publisher_name("D. Bogue")
        assert result == "David Bogue"

    def test_normalizes_ampersand_co_punctuation(self):
        result = auto_correct_publisher_name("Harper & Co")
        assert result == "Harper & Co."

    def test_preserves_clean_name(self):
        result = auto_correct_publisher_name("Oxford University Press")
        assert result == "Oxford University Press"

    def test_handles_multiple_issues(self):
        result = auto_correct_publisher_name("D. Bogue, Fleet-Street (First Edition)")
        assert result == "David Bogue"

    def test_strips_whitespace(self):
        result = auto_correct_publisher_name("  Harper & Brothers  ")
        assert result == "Harper & Brothers"
