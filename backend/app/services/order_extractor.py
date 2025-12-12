import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ExtractionResult(BaseModel):
    order_number: Optional[str] = None
    item_price: Optional[float] = None
    shipping: Optional[float] = None
    total: Optional[float] = None
    currency: str = "USD"
    purchase_date: Optional[str] = None
    platform: str = "eBay"
    estimated_delivery: Optional[str] = None
    tracking_number: Optional[str] = None
    confidence: float = 0.0
    used_llm: bool = False
    field_confidence: dict = {}


PATTERNS = {
    "order_number": [
        (r"\b(\d{2}-\d{5}-\d{5})\b", 0.99),  # eBay format
        (r"[Oo]rder\s*(?:#|number|num)?[:\s]*(\d[\d-]+\d)", 0.95),
    ],
    "total": [
        (r"[Oo]rder\s+[Tt]otal[:\s]*([£$€])\s*([\d,]+\.?\d*)", 0.95),
        (r"[Tt]otal[:\s]*([£$€])\s*([\d,]+\.?\d*)", 0.90),
    ],
    "item_price": [
        (r"[Ii]tem\s+[Pp]rice[:\s]*([£$€])\s*([\d,]+\.?\d*)", 0.95),
        (r"[Pp]rice[:\s]*([£$€])\s*([\d,]+\.?\d*)", 0.85),
    ],
    "shipping": [
        (r"[Ss]hipping[:\s]*([£$€])\s*([\d,]+\.?\d*)", 0.95),
        (r"[Pp]ostage[:\s]*([£$€])\s*([\d,]+\.?\d*)", 0.90),
    ],
    "tracking": [
        (r"\b(\d{20,30})\b", 0.85),  # Long numeric tracking
        (r"[Tt]racking[:\s#]*([A-Z0-9]{10,30})", 0.95),
    ],
    "date": [
        (r"(\w{3}\s+\d{1,2},?\s+\d{4})", 0.90),  # Jan 15, 2025
        (r"(\d{4}-\d{2}-\d{2})", 0.95),  # ISO format
        (r"(\d{1,2}/\d{1,2}/\d{4})", 0.85),  # MM/DD/YYYY
    ],
    "delivery": [
        (r"[Ee]stimated\s+[Dd]elivery[:\s]+(.+?)(?:\n|$)", 0.90),
        (r"[Dd]elivery[:\s]+(\w{3}\s+\d{1,2}(?:\s*-\s*\d{1,2})?)", 0.85),
    ],
}

CURRENCY_MAP = {"£": "GBP", "$": "USD", "€": "EUR"}


def parse_price(match: tuple) -> tuple[str, float]:
    """Parse currency symbol and amount from regex match."""
    currency_symbol, amount = match
    currency = CURRENCY_MAP.get(currency_symbol, "USD")
    value = float(amount.replace(",", ""))
    return currency, value


def extract_with_regex(text: str) -> ExtractionResult:
    """Extract order details using regex patterns."""
    result = ExtractionResult()
    field_confidence = {}

    # Order number
    for pattern, conf in PATTERNS["order_number"]:
        match = re.search(pattern, text)
        if match:
            result.order_number = match.group(1)
            field_confidence["order_number"] = conf
            break

    # Prices (total, item_price, shipping)
    for field in ["total", "item_price", "shipping"]:
        for pattern, conf in PATTERNS[field]:
            match = re.search(pattern, text)
            if match:
                currency, value = parse_price(match.groups())
                setattr(result, field, value)
                if field == "total":
                    result.currency = currency
                field_confidence[field] = conf
                break

    # Tracking number
    for pattern, conf in PATTERNS["tracking"]:
        match = re.search(pattern, text)
        if match:
            result.tracking_number = match.group(1)
            field_confidence["tracking_number"] = conf
            break

    # Purchase date
    for pattern, conf in PATTERNS["date"]:
        match = re.search(pattern, text)
        if match:
            date_str = match.group(1)
            try:
                # Try multiple date formats
                for fmt in ["%b %d, %Y", "%b %d %Y", "%Y-%m-%d", "%m/%d/%Y"]:
                    try:
                        dt = datetime.strptime(date_str, fmt)
                        result.purchase_date = dt.strftime("%Y-%m-%d")
                        field_confidence["purchase_date"] = conf
                        break
                    except ValueError:
                        continue
            except Exception:
                pass
            if result.purchase_date:
                break

    # Estimated delivery
    for pattern, conf in PATTERNS["delivery"]:
        match = re.search(pattern, text)
        if match:
            result.estimated_delivery = match.group(1).strip()
            field_confidence["estimated_delivery"] = conf
            break

    # Calculate overall confidence
    if field_confidence:
        result.confidence = sum(field_confidence.values()) / len(field_confidence)
    result.field_confidence = field_confidence

    return result
