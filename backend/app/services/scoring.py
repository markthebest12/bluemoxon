"""Scoring engine for book acquisition evaluation."""

from decimal import Decimal


def calculate_investment_grade(
    purchase_price: Decimal | None,
    value_mid: Decimal | None,
) -> int:
    """
    Calculate investment grade based on discount percentage.

    Returns score 0-100:
    - 70%+ discount: 100
    - 60-69%: 85
    - 50-59%: 70
    - 40-49%: 55
    - 30-39%: 35
    - 20-29%: 20
    - <20%: 5
    - No data: 0
    """
    if purchase_price is None or value_mid is None:
        return 0

    if value_mid <= 0:
        return 0

    discount_pct = float((value_mid - purchase_price) / value_mid * 100)

    if discount_pct >= 70:
        return 100
    elif discount_pct >= 60:
        return 85
    elif discount_pct >= 50:
        return 70
    elif discount_pct >= 40:
        return 55
    elif discount_pct >= 30:
        return 35
    elif discount_pct >= 20:
        return 20
    else:
        return 5
