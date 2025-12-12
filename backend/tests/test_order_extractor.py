import pytest
from app.services.order_extractor import extract_with_regex

SAMPLE_EBAY_EMAIL = """
Your order has been confirmed!
Order number: 21-13904-88107

Item: First Edition Book
Item price: £239.00
Shipping: £17.99
Order total: £256.99

Estimated delivery: Jan 20-25

Tracking number: 9400111899223847560123
"""


def test_extracts_order_number():
    result = extract_with_regex(SAMPLE_EBAY_EMAIL)
    assert result.order_number == "21-13904-88107"
    assert result.field_confidence["order_number"] >= 0.95


def test_extracts_prices():
    result = extract_with_regex(SAMPLE_EBAY_EMAIL)
    assert result.item_price == 239.00
    assert result.shipping == 17.99
    assert result.total == 256.99
    assert result.currency == "GBP"


def test_extracts_tracking():
    result = extract_with_regex(SAMPLE_EBAY_EMAIL)
    assert result.tracking_number == "9400111899223847560123"


def test_overall_confidence():
    result = extract_with_regex(SAMPLE_EBAY_EMAIL)
    assert result.confidence >= 0.8


def test_empty_text():
    result = extract_with_regex("")
    assert result.confidence == 0.0
    assert result.order_number is None


def test_partial_extraction():
    text = "Order total: $50.00"
    result = extract_with_regex(text)
    assert result.total == 50.00
    assert result.currency == "USD"
    assert result.order_number is None
