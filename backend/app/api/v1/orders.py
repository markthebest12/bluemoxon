"""Order extraction API endpoints."""

import json
import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_editor
from app.db import get_db
from app.models.admin_config import AdminConfig
from app.services.bedrock import get_bedrock_client
from app.services.order_extractor import extract_with_regex

router = APIRouter()
logger = logging.getLogger(__name__)


class ExtractRequest(BaseModel):
    """Request to extract order details from text."""

    text: str


class ExtractResponse(BaseModel):
    """Response with extracted order details."""

    order_number: str | None = None
    item_price: float | None = None
    shipping: float | None = None
    total: float | None = None
    currency: str = "USD"
    total_usd: float | None = None
    purchase_date: str | None = None
    platform: str = "eBay"
    estimated_delivery: str | None = None
    tracking_number: str | None = None
    confidence: float = 0.0
    used_llm: bool = False
    field_confidence: dict = {}


LLM_PROMPT = """Extract order details from this text. Return JSON only:
{
  "order_number": "string or null",
  "item_price": number or null,
  "shipping": number or null,
  "total": number or null,
  "currency": "USD|GBP|EUR",
  "purchase_date": "YYYY-MM-DD or null",
  "estimated_delivery": "string or null",
  "tracking_number": "string or null"
}

Text:
"""


async def extract_with_llm(text: str) -> dict:
    """Use Bedrock Claude to extract order details.

    Args:
        text: The order text to extract from

    Returns:
        Dict with extracted fields

    Raises:
        Exception: If Bedrock call fails
    """
    client = get_bedrock_client()
    response = client.invoke_model(
        modelId="anthropic.claude-3-haiku-20240307-v1:0",
        body=json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,
                "messages": [{"role": "user", "content": LLM_PROMPT + text}],
            }
        ),
    )
    result = json.loads(response["body"].read())
    content = result["content"][0]["text"]

    # Extract JSON from response
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Try to find JSON in response
        match = re.search(r"\{[^}]+\}", content, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {}


def get_conversion_rate(currency: str, db: Session) -> float:
    """Get currency conversion rate from admin config.

    Args:
        currency: Currency code (USD, GBP, EUR)
        db: Database session

    Returns:
        Conversion rate to USD
    """
    if currency == "USD":
        return 1.0

    key = f"{currency.lower()}_to_usd_rate"
    config = db.query(AdminConfig).filter(AdminConfig.key == key).first()

    if config:
        return float(config.value)

    # Fallback defaults (update via scripts/update-exchange-rates.sh)
    fallback_rates = {"GBP": 1.35, "EUR": 1.17}
    rate = fallback_rates.get(currency)

    if rate is not None:
        logger.warning(
            "Using fallback exchange rate for %s: %.4f (no DB config found)",
            currency,
            rate,
        )
        return rate

    logger.warning(
        "Unknown currency %s, defaulting to 1.0 (no conversion)",
        currency,
    )
    return 1.0


@router.post("/extract", response_model=ExtractResponse)
async def extract_order(
    request: ExtractRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Extract order details from pasted text.

    Args:
        request: Request with order text
        db: Database session

    Returns:
        ExtractResponse with extracted fields and confidence scores

    Raises:
        HTTPException: If text is empty
    """
    if not request.text.strip():
        raise HTTPException(400, "Text is required")

    # Try regex first
    result = extract_with_regex(request.text)

    # If confidence too low, try LLM
    if result.confidence < 0.8:
        try:
            llm_result = await extract_with_llm(request.text)
            if llm_result:
                # Merge LLM results with higher confidence
                for field, value in llm_result.items():
                    if value is not None:
                        current_conf = result.field_confidence.get(field, 0)
                        if current_conf < 0.7:
                            setattr(result, field, value)
                            result.field_confidence[field] = 0.85
                result.used_llm = True
                # Recalculate overall confidence
                if result.field_confidence:
                    result.confidence = sum(result.field_confidence.values()) / len(
                        result.field_confidence
                    )
        except Exception as e:
            # Log but continue with regex results
            logger.warning(f"LLM extraction failed: {e}")

    # Convert to USD if needed
    response = ExtractResponse(**result.model_dump())
    if response.total and response.currency != "USD":
        rate = get_conversion_rate(response.currency, db)
        response.total_usd = round(response.total * rate, 2)
    elif response.total:
        response.total_usd = response.total

    return response
