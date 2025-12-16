"""Eval Runbook generation service.

This service generates the comprehensive evaluation report based on:
1. Book metadata from eBay listing
2. Book's existing attributes (publisher tier, binder, condition, etc.)
3. Claude Vision analysis of listing images for condition assessment
4. FMV comparison from eBay sold listings and AbeBooks
"""

import json
import logging
import re
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Book, BookImage, EvalRunbook
from app.services.bedrock import (
    fetch_book_images_for_bedrock,
    get_bedrock_client,
    get_model_id,
)
from app.services.fmv_lookup import lookup_fmv

logger = logging.getLogger(__name__)

ACQUIRE_THRESHOLD = 80

# Victorian era: 1837 (Victoria's accession) to 1901 (her death)
VICTORIAN_START = 1837
VICTORIAN_END = 1901

# Tier 1 binders (premium binding attribution)
TIER_1_BINDERS = {
    "Rivière & Son",
    "Riviere",
    "Zaehnsdorf",
    "Sangorski & Sutcliffe",
    "Sangorski",
    "Cobden-Sanderson",
    "Bedford",
}


def _calculate_publisher_score(book: Book) -> tuple[int, str]:
    """Calculate Tier 1 Publisher score (max 20 points)."""
    if book.publisher and hasattr(book.publisher, "tier") and book.publisher.tier == "TIER_1":
        return 20, f"✓ {book.publisher.name} (Tier 1)"
    elif book.publisher:
        return 0, f"{book.publisher.name} - NOT Tier 1"
    return 0, "No publisher identified"


def _calculate_victorian_score(book: Book) -> tuple[int, str]:
    """Calculate Victorian Era score (max 30 points)."""
    if book.year_start:
        if VICTORIAN_START <= book.year_start <= VICTORIAN_END:
            return 30, f"✓ {book.year_start}"
        else:
            return 0, f"{book.year_start} - outside Victorian era"
    return 0, "Publication year unknown"


def _calculate_complete_set_score(book: Book) -> tuple[int, str]:
    """Calculate Complete Set score (max 20 points)."""
    if book.is_complete:
        if book.volumes == 1:
            return 20, "✓ Single volume"
        else:
            return 20, f"✓ Complete set ({book.volumes} volumes)"
    else:
        return 0, f"Incomplete - missing volumes from {book.volumes}-volume set"


def _calculate_condition_score(book: Book) -> tuple[int, str]:
    """Calculate Condition score (max 15 points)."""
    condition = book.condition_grade or ""
    condition_lower = condition.lower()

    # Score based on condition grade
    if "fine" in condition_lower or "mint" in condition_lower:
        points = 15
        notes = f"✓ {condition}"
    elif "very good" in condition_lower or "vg+" in condition_lower:
        points = 12
        notes = f"✓ {condition}"
    elif "good" in condition_lower:
        points = 10
        notes = f"{condition}"
    elif "fair" in condition_lower:
        points = 5
        notes = f"{condition} (condition penalty)"
    elif "poor" in condition_lower:
        points = 0
        notes = f"{condition} (significant condition issues)"
    else:
        points = 8  # Unknown condition, assume average
        notes = "Condition not assessed"

    # Check for foxing in condition_notes
    if book.condition_notes and "foxing" in book.condition_notes.lower():
        if "heavy" in book.condition_notes.lower() or "significant" in book.condition_notes.lower():
            points = max(0, points - 5)
            notes += " (foxing penalty)"
        else:
            points = max(0, points - 2)
            notes += " (minor foxing)"

    return points, notes


def _calculate_binding_score(book: Book) -> tuple[int, str]:
    """Calculate Premium Binding score (max 15 points)."""
    if book.binder:
        binder_name = book.binder.name
        # Check if Tier 1 binder
        if any(tier1 in binder_name for tier1 in TIER_1_BINDERS):
            return 15, f"✓ {binder_name} (premium binder)"
        elif hasattr(book.binder, "tier") and book.binder.tier == "TIER_2":
            return 10, f"{binder_name} (Tier 2 binder)"
        else:
            return 5, f"{binder_name}"
    elif book.binding_type:
        binding_lower = book.binding_type.lower()
        if "morocco" in binding_lower or "leather" in binding_lower:
            return 5, f"{book.binding_type} (no binder signature)"
        return 0, f"{book.binding_type}"
    return 0, "No binder signature"


def _calculate_price_score(
    asking_price: float | None,
    fmv_low: float | None,
    fmv_high: float | None,
) -> tuple[int, str]:
    """Calculate Price vs FMV score (max 20 points)."""
    if not asking_price:
        return 0, "No asking price"

    if fmv_low and fmv_high:
        fmv_mid = (fmv_low + fmv_high) / 2
        discount_pct = ((fmv_mid - asking_price) / fmv_mid) * 100

        if discount_pct >= 30:
            return 20, f"{discount_pct:.0f}% below FMV (excellent)"
        elif discount_pct >= 15:
            return 10, f"{discount_pct:.0f}% below FMV (good)"
        elif discount_pct >= 0:
            return 5, "At or near FMV"
        else:
            return 0, f"{abs(discount_pct):.0f}% above FMV"

    return 0, "FMV not yet determined"


def _analyze_images_with_claude(
    images: list[BookImage],
    book_title: str,
    listing_description: str | None = None,
) -> dict:
    """Analyze book images using Claude Vision for condition assessment.

    Args:
        images: List of BookImage objects
        book_title: Title of the book for context
        listing_description: Optional seller description

    Returns:
        Dict with:
            - condition_grade: Assessed condition (Fine, VG+, Good, Fair, Poor)
            - condition_positives: List of positive condition observations
            - condition_negatives: List of negative condition observations
            - critical_issues: List of issues that significantly impact value
            - item_identification: Dict with identified details
            - binding_analysis: Notes about binding quality
    """
    if not images:
        logger.warning("No images provided for Claude analysis")
        return {
            "condition_grade": None,
            "condition_positives": [],
            "condition_negatives": [],
            "critical_issues": [],
            "item_identification": {},
            "binding_analysis": None,
        }

    # Load images for Bedrock
    image_blocks = fetch_book_images_for_bedrock(images, max_images=15)

    if not image_blocks:
        logger.warning("Failed to load any images for Claude analysis")
        return {
            "condition_grade": None,
            "condition_positives": [],
            "condition_negatives": [],
            "critical_issues": [],
            "item_identification": {},
            "binding_analysis": None,
        }

    # Build the analysis prompt
    prompt = f"""Analyze these images of an antiquarian book listing for acquisition evaluation.

BOOK: {book_title}

{f"SELLER DESCRIPTION: {listing_description}" if listing_description else ""}

Examine all images carefully and provide a detailed condition assessment. Look for:
- Binding condition (tight, loose, cracked, rebacked)
- Cover wear (rubbing, fading, stains, scratches)
- Spine condition (text legibility, sunning, cracking)
- Page condition (foxing, toning, tears, stains)
- Hinges (tight, starting, cracked)
- Any repairs or restoration
- Completeness (plates, maps, bookplates)
- Notable features (gilt edges, marbled endpapers, raised bands)

Provide your analysis as JSON:
{{
    "condition_grade": "Fine|Very Good|Good|Fair|Poor",
    "condition_positives": [
        "Specific positive observation 1",
        "Specific positive observation 2"
    ],
    "condition_negatives": [
        "Specific negative observation 1",
        "Specific negative observation 2"
    ],
    "critical_issues": [
        "Issues that significantly impact value (empty if none)"
    ],
    "item_identification": {{
        "binding_type": "Full leather/Half leather/Cloth/etc",
        "binding_color": "Description of binding color",
        "decorative_elements": "Gilt, tooling, raised bands, etc",
        "estimated_age": "Victorian/Edwardian/Modern/etc",
        "binder_signature": "Name if visible, or null",
        "illustrations": "Description if present"
    }},
    "binding_analysis": "Detailed paragraph about the binding quality and attribution"
}}

Return ONLY valid JSON, no other text."""

    # Build message with images
    content = [{"type": "text", "text": prompt}]
    content.extend(image_blocks)

    try:
        client = get_bedrock_client()
        model_id = get_model_id("sonnet")

        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "messages": [{"role": "user", "content": content}],
            }
        )

        logger.info(f"Invoking Claude Vision for condition analysis ({len(image_blocks)} images)")
        response = client.invoke_model(
            modelId=model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )

        response_body = json.loads(response["body"].read())
        result_text = response_body["content"][0]["text"]

        # Extract JSON from response
        json_match = re.search(r"\{[\s\S]*\}", result_text)
        if json_match:
            analysis = json.loads(json_match.group())
            logger.info(f"Claude condition analysis: {analysis.get('condition_grade', 'Unknown')}")
            return analysis

        logger.warning("No JSON found in Claude response")
        return {
            "condition_grade": None,
            "condition_positives": [],
            "condition_negatives": [],
            "critical_issues": [],
            "item_identification": {},
            "binding_analysis": None,
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude response as JSON: {e}")
        return {
            "condition_grade": None,
            "condition_positives": [],
            "condition_negatives": [],
            "critical_issues": [],
            "item_identification": {},
            "binding_analysis": None,
        }
    except Exception as e:
        logger.error(f"Claude Vision analysis failed: {e}")
        return {
            "condition_grade": None,
            "condition_positives": [],
            "condition_negatives": [],
            "critical_issues": [],
            "item_identification": {},
            "binding_analysis": None,
        }


def generate_eval_runbook(
    book: Book,
    listing_data: dict,
    db: Session,
    run_ai_analysis: bool = True,
    run_fmv_lookup: bool = True,
) -> EvalRunbook:
    """Generate eval runbook for a book with AI analysis and FMV lookup.

    Args:
        book: Book model instance with relationships loaded (including images)
        listing_data: Data from listing import containing:
            - price: Asking price
            - author: Author name
            - publisher: Publisher name
            - description: Seller description (optional)
        db: Database session
        run_ai_analysis: Whether to run Claude Vision analysis on images
        run_fmv_lookup: Whether to look up FMV from eBay/AbeBooks

    Returns:
        Created EvalRunbook instance
    """
    logger.info(f"Generating eval runbook for book {book.id}: {book.title}")

    asking_price = listing_data.get("price")
    author_name = listing_data.get("author") or (book.author.name if book.author else None)

    # Initialize AI analysis results
    ai_analysis = {
        "condition_grade": None,
        "condition_positives": [],
        "condition_negatives": [],
        "critical_issues": [],
        "item_identification": {},
        "binding_analysis": None,
    }

    # Run Claude Vision analysis if enabled and images available
    if run_ai_analysis and book.images:
        logger.info(f"Running Claude Vision analysis on {len(book.images)} images")
        ai_analysis = _analyze_images_with_claude(
            images=list(book.images),
            book_title=book.title,
            listing_description=listing_data.get("description"),
        )

    # Initialize FMV data
    fmv_data = {
        "ebay_comparables": [],
        "abebooks_comparables": [],
        "fmv_low": None,
        "fmv_high": None,
        "fmv_notes": "",
    }

    # Run FMV lookup if enabled (with error handling to not block import)
    if run_fmv_lookup:
        try:
            logger.info(f"Looking up FMV for: {book.title}")
            fmv_data = lookup_fmv(
                title=book.title,
                author=author_name,
                max_per_source=5,
            )
        except Exception as e:
            logger.warning(f"FMV lookup failed (continuing without FMV): {e}")
            fmv_data["fmv_notes"] = "FMV lookup failed - can be retried later"

    # Use AI-assessed condition grade if available, otherwise fall back to book's grade
    condition_grade = ai_analysis.get("condition_grade") or book.condition_grade

    # Use FMV from lookup, or fall back to book's existing values
    fmv_low = fmv_data.get("fmv_low")
    fmv_high = fmv_data.get("fmv_high")
    if not fmv_low and book.value_low:
        fmv_low = float(book.value_low)
    if not fmv_high and book.value_high:
        fmv_high = float(book.value_high)

    # Calculate each scoring criterion
    publisher_points, publisher_notes = _calculate_publisher_score(book)
    victorian_points, victorian_notes = _calculate_victorian_score(book)
    complete_points, complete_notes = _calculate_complete_set_score(book)
    binding_points, binding_notes = _calculate_binding_score(book)

    # Use AI condition grade for scoring if available
    if condition_grade:
        # Temporarily set condition_grade on book for scoring
        original_grade = book.condition_grade
        book.condition_grade = condition_grade
        condition_points, condition_notes = _calculate_condition_score(book)
        book.condition_grade = original_grade
    else:
        condition_points, condition_notes = _calculate_condition_score(book)

    price_points, price_notes = _calculate_price_score(asking_price, fmv_low, fmv_high)

    score_breakdown = {
        "Tier 1 Publisher": {"points": publisher_points, "notes": publisher_notes},
        "Victorian Era": {"points": victorian_points, "notes": victorian_notes},
        "Complete Set": {"points": complete_points, "notes": complete_notes},
        "Condition": {"points": condition_points, "notes": condition_notes},
        "Premium Binding": {"points": binding_points, "notes": binding_notes},
        "Price vs FMV": {"points": price_points, "notes": price_notes},
    }

    total_score = sum(item["points"] for item in score_breakdown.values())
    recommendation = "ACQUIRE" if total_score >= ACQUIRE_THRESHOLD else "PASS"

    # Build comprehensive analysis narrative
    narrative_parts = []

    # Score summary
    if total_score >= ACQUIRE_THRESHOLD:
        narrative_parts.append(
            f"**RECOMMENDATION: ACQUIRE** - This book scores {total_score}/120, "
            f"meeting the {ACQUIRE_THRESHOLD}-point acquisition threshold."
        )
    else:
        points_needed = ACQUIRE_THRESHOLD - total_score
        narrative_parts.append(
            f"**RECOMMENDATION: PASS** - This book scores {total_score}/120, "
            f"{points_needed} points below the acquisition threshold."
        )

    # Add binding analysis from AI if available
    if ai_analysis.get("binding_analysis"):
        narrative_parts.append(f"\n\n**Binding Analysis:** {ai_analysis['binding_analysis']}")
    elif binding_points >= 15 and book.binder:
        narrative_parts.append(
            f"\n\n**Binding:** The {book.binder.name} binding adds significant collector value."
        )

    # Add condition summary
    if ai_analysis.get("condition_positives") or ai_analysis.get("condition_negatives"):
        narrative_parts.append(f"\n\n**Condition:** Assessed as {condition_grade or 'Unknown'}.")
    elif condition_grade:
        narrative_parts.append(f"\n\n**Condition:** {condition_grade}")

    # Add critical issues if any
    if ai_analysis.get("critical_issues"):
        issues = ai_analysis["critical_issues"]
        narrative_parts.append(f"\n\n**Critical Issues:** {'; '.join(issues)}")

    # Add FMV context
    if fmv_low and fmv_high:
        narrative_parts.append(
            f"\n\n**Fair Market Value:** ${fmv_low:.0f} - ${fmv_high:.0f} "
            f"based on {len(fmv_data.get('ebay_comparables', []))} eBay sold listings "
            f"and {len(fmv_data.get('abebooks_comparables', []))} AbeBooks listings."
        )
        if asking_price:
            if asking_price < fmv_low:
                narrative_parts.append(f"Asking price of ${asking_price:.0f} is below FMV range.")
            elif asking_price > fmv_high:
                narrative_parts.append(f"Asking price of ${asking_price:.0f} is above FMV range.")

    # Add era context
    if victorian_points == 0 and book.year_start:
        narrative_parts.append(
            f"\n\n**Era:** Published in {book.year_start}, outside the Victorian era target range (1837-1901)."
        )

    analysis_narrative = "".join(narrative_parts)

    # Build comprehensive item identification
    item_identification = {
        "Title": book.title,
        "Author": author_name or "Unknown",
        "Publisher": listing_data.get("publisher")
        or (book.publisher.name if book.publisher else "Unknown"),
        "Year": str(book.year_start) if book.year_start else "Unknown",
        "Binder": book.binder.name if book.binder else None,
        "Volumes": book.volumes,
        "Binding Type": book.binding_type,
    }

    # Merge AI-identified details
    if ai_analysis.get("item_identification"):
        ai_ident = ai_analysis["item_identification"]
        if ai_ident.get("binding_type") and not item_identification.get("Binding Type"):
            item_identification["Binding Type"] = ai_ident["binding_type"]
        if ai_ident.get("decorative_elements"):
            item_identification["Decorative Elements"] = ai_ident["decorative_elements"]
        if ai_ident.get("binder_signature") and not item_identification.get("Binder"):
            item_identification["Binder"] = ai_ident["binder_signature"]
        if ai_ident.get("illustrations"):
            item_identification["Illustrations"] = ai_ident["illustrations"]

    runbook = EvalRunbook(
        book_id=book.id,
        total_score=total_score,
        score_breakdown=score_breakdown,
        recommendation=recommendation,
        original_asking_price=Decimal(str(asking_price)) if asking_price else None,
        current_asking_price=Decimal(str(asking_price)) if asking_price else None,
        fmv_low=Decimal(str(fmv_low)) if fmv_low else None,
        fmv_high=Decimal(str(fmv_high)) if fmv_high else None,
        condition_grade=condition_grade,
        condition_positives=ai_analysis.get("condition_positives") or [],
        condition_negatives=ai_analysis.get("condition_negatives") or [],
        critical_issues=ai_analysis.get("critical_issues") or [],
        ebay_comparables=fmv_data.get("ebay_comparables") or [],
        abebooks_comparables=fmv_data.get("abebooks_comparables") or [],
        item_identification=item_identification,
        analysis_narrative=analysis_narrative,
        generated_at=datetime.utcnow(),
    )

    db.add(runbook)
    db.commit()
    db.refresh(runbook)

    logger.info(
        f"Created eval runbook {runbook.id} for book {book.id}, "
        f"score={total_score}, recommendation={recommendation}, "
        f"ai_analysis={'yes' if run_ai_analysis else 'no'}, "
        f"fmv_lookup={'yes' if run_fmv_lookup else 'no'}"
    )

    return runbook


def generate_eval_runbook_quick(
    book: Book,
    listing_data: dict,
    db: Session,
) -> EvalRunbook:
    """Generate a quick eval runbook without AI analysis or FMV lookup.

    This is the original fast path for when you don't need full analysis.

    Args:
        book: Book model instance with relationships loaded
        listing_data: Data from listing import
        db: Database session

    Returns:
        Created EvalRunbook instance
    """
    return generate_eval_runbook(
        book=book,
        listing_data=listing_data,
        db=db,
        run_ai_analysis=False,
        run_fmv_lookup=False,
    )
