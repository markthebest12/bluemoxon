"""Tests for set completion detection service."""


class TestRomanToInt:
    """Tests for Roman numeral to integer conversion."""

    def test_roman_i_returns_1(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("I") == 1

    def test_roman_v_returns_5(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("V") == 5

    def test_roman_viii_returns_8(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("VIII") == 8

    def test_roman_xii_returns_12(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("XII") == 12

    def test_roman_iv_returns_4(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("IV") == 4

    def test_roman_ix_returns_9(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("IX") == 9

    def test_roman_lowercase_works(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("viii") == 8

    def test_roman_invalid_returns_none(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("INVALID") is None

    def test_roman_xiii_exceeds_limit_returns_none(self):
        from app.services.set_detection import roman_to_int

        assert roman_to_int("XIII") is None
