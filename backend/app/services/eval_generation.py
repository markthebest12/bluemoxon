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
from app.services.tiered_scoring import (
    QUALITY_FLOOR,
    STRATEGIC_FIT_FLOOR,
    calculate_combined_score,
    calculate_price_position,
    calculate_quality_score,
    calculate_strategic_fit_score,
    calculate_suggested_offer,
    determine_recommendation_tier,
    generate_reasoning,
)

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

# Author-publisher requirements (author_name -> required_publisher_name)
AUTHOR_PUBLISHER_REQUIREMENTS = {
    "Wilkie Collins": "Bentley",
    "Charles Dickens": "Chapman",
    # Add more as needed
}


def _check_publisher_matches_author(author_name: str | None, publisher_name: str | None) -> bool:
    """Check if publisher matches the required publisher for this author."""
    if not author_name or not publisher_name:
        return False
    required = AUTHOR_PUBLISHER_REQUIREMENTS.get(author_name)
    if not required:
        return True  # No requirement = matches
    return required.lower() in publisher_name.lower()


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
    """Calculate Premium Binding score (max 15 points).

    Premium binder points (15 for Tier 1, 10 for Tier 2) are only awarded
    when binding_authenticated is True, indicating the binder attribution
    has been confirmed via visible signature or stamp.
    """
    if book.binder:
        binder_name = book.binder.name
        is_authenticated = getattr(book, "binding_authenticated", False) or False

        # Check if Tier 1 binder
        if any(tier1 in binder_name for tier1 in TIER_1_BINDERS):
            if is_authenticated:
                return 15, f"✓ {binder_name} (premium binder, authenticated)"
            else:
                # Binder identified but not authenticated - no premium points
                return 5, f"{binder_name} (unconfirmed attribution)"
        elif hasattr(book.binder, "tier") and book.binder.tier == "TIER_2":
            if is_authenticated:
                return 10, f"{binder_name} (Tier 2 binder, authenticated)"
            else:
                return 5, f"{binder_name} (unconfirmed attribution)"
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
            "unrelated_images": [],
            "unrelated_reasons": {},
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
            "unrelated_images": [],
            "unrelated_reasons": {},
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

IMAGE RELEVANCE: For each image, determine if it shows the actual book being sold.
Mark as UNRELATED any images that are:
- Seller store logos or banners
- "Visit My Store" promotional images
- Completely different books (different titles, authors, or editions)
- Generic stock photos not of this specific item
- Seller contact/shipping information graphics

Return the 0-based index of each unrelated image in the unrelated_images array.
If ALL images show the book being sold, return an empty array.

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
    "binding_analysis": "Detailed paragraph about the binding quality and attribution",
    "unrelated_images": [17, 18, 19],
    "unrelated_reasons": {{
        "17": "Brief reason why image 17 is unrelated",
        "18": "Brief reason why image 18 is unrelated"
    }}
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
            "unrelated_images": [],
            "unrelated_reasons": {},
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
            "unrelated_images": [],
            "unrelated_reasons": {},
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
            "unrelated_images": [],
            "unrelated_reasons": {},
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
        "fmv_confidence": None,
        "fmv_notes": "",
    }

    # Run FMV lookup if enabled (with error handling to not block import)
    if run_fmv_lookup:
        try:
            logger.info(f"Looking up FMV for: {book.title}")
            # Get binder name from relationship if available
            binder_name = book.binder.name if book.binder else None
            fmv_data = lookup_fmv(
                title=book.title,
                author=author_name,
                max_per_source=5,
                volumes=book.volumes or 1,
                binding_type=book.binding_type,
                binder=binder_name,
                edition=book.edition,
                publication_year=book.year_start,
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

    # Calculate tiered recommendation scores
    publisher_name = book.publisher.name if book.publisher else None
    binder_name = book.binder.name if book.binder else None

    # Check if publisher matches author requirement
    publisher_matches = _check_publisher_matches_author(author_name, publisher_name)

    # Count author's books in collection
    author_book_count = 0
    if book.author_id:
        author_book_count = (
            db.query(Book).filter(Book.author_id == book.author_id, Book.id != book.id).count()
        )

    # Check for duplicates
    is_duplicate = False
    if book.author_id:
        from app.services.scoring import is_duplicate_title

        other_books = (
            db.query(Book).filter(Book.author_id == book.author_id, Book.id != book.id).all()
        )
        for other in other_books:
            if is_duplicate_title(book.title, other.title):
                is_duplicate = True
                break

    # Calculate quality score
    tiered_quality_score = calculate_quality_score(
        publisher_tier=book.publisher.tier if book.publisher else None,
        binder_tier=book.binder.tier if book.binder else None,
        year_start=book.year_start,
        condition_grade=condition_grade,
        is_complete=book.is_complete,
        author_priority_score=book.author.priority_score if book.author else 0,
        volume_count=book.volumes or 1,
        is_duplicate=is_duplicate,
    )

    # Calculate strategic fit score
    tiered_strategic_fit_score = calculate_strategic_fit_score(
        publisher_matches_author_requirement=publisher_matches,
        author_book_count=author_book_count,
        completes_set=False,  # TODO: Implement set completion detection
    )

    # Calculate combined score and price position
    tiered_combined_score = calculate_combined_score(
        tiered_quality_score, tiered_strategic_fit_score
    )
    fmv_mid = None
    if fmv_low and fmv_high:
        fmv_mid = (Decimal(str(fmv_low)) + Decimal(str(fmv_high))) / 2

    tiered_price_position = calculate_price_position(
        asking_price=Decimal(str(asking_price)) if asking_price else None,
        fmv_mid=fmv_mid,
    )

    # Check floor conditions
    strategic_floor_applied = tiered_strategic_fit_score < STRATEGIC_FIT_FLOOR
    quality_floor_applied = tiered_quality_score < QUALITY_FLOOR

    # Determine recommendation tier
    recommendation_tier = determine_recommendation_tier(
        combined_score=tiered_combined_score,
        price_position=tiered_price_position,
        quality_score=tiered_quality_score,
        strategic_fit_score=tiered_strategic_fit_score,
    )

    # Calculate suggested offer for CONDITIONAL
    suggested_offer = None
    if recommendation_tier == "CONDITIONAL" and fmv_mid:
        suggested_offer = calculate_suggested_offer(
            combined_score=tiered_combined_score,
            fmv_mid=fmv_mid,
            strategic_floor_applied=strategic_floor_applied,
            quality_floor_applied=quality_floor_applied,
        )

    # Calculate discount percent for reasoning
    discount_percent = 0
    if asking_price and fmv_mid:
        discount_percent = int(((float(fmv_mid) - asking_price) / float(fmv_mid)) * 100)

    # Generate reasoning
    recommendation_reasoning = generate_reasoning(
        recommendation_tier=recommendation_tier,
        quality_score=tiered_quality_score,
        strategic_fit_score=tiered_strategic_fit_score,
        price_position=tiered_price_position,
        discount_percent=discount_percent,
        publisher_name=publisher_name,
        binder_name=binder_name,
        author_name=author_name,
        strategic_floor_applied=strategic_floor_applied,
        quality_floor_applied=quality_floor_applied,
        suggested_offer=suggested_offer,
    )

    # Map tier to legacy recommendation for backward compatibility
    recommendation = "ACQUIRE" if recommendation_tier in ("STRONG_BUY", "BUY") else "PASS"

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
        # Tiered recommendation fields
        recommendation_tier=recommendation_tier,
        quality_score=tiered_quality_score,
        strategic_fit_score=tiered_strategic_fit_score,
        combined_score=tiered_combined_score,
        price_position=tiered_price_position,
        suggested_offer=suggested_offer,
        recommendation_reasoning=recommendation_reasoning,
        strategic_floor_applied=strategic_floor_applied,
        quality_floor_applied=quality_floor_applied,
        scoring_version="2025-01",
        score_source="eval_runbook",
        last_scored_price=Decimal(str(asking_price)) if asking_price else None,
        # Pricing and FMV
        original_asking_price=Decimal(str(asking_price)) if asking_price else None,
        current_asking_price=Decimal(str(asking_price)) if asking_price else None,
        fmv_low=Decimal(str(fmv_low)) if fmv_low else None,
        fmv_high=Decimal(str(fmv_high)) if fmv_high else None,
        fmv_notes=fmv_data.get("fmv_notes"),
        fmv_confidence=fmv_data.get("fmv_confidence"),
        # Condition assessment
        condition_grade=condition_grade,
        condition_positives=ai_analysis.get("condition_positives") or [],
        condition_negatives=ai_analysis.get("condition_negatives") or [],
        critical_issues=ai_analysis.get("critical_issues") or [],
        # Comparables
        ebay_comparables=fmv_data.get("ebay_comparables") or [],
        abebooks_comparables=fmv_data.get("abebooks_comparables") or [],
        # Identification and narrative
        item_identification=item_identification,
        analysis_narrative=analysis_narrative,
        generated_at=datetime.utcnow(),
    )

    db.add(runbook)
    db.commit()
    db.refresh(runbook)

    logger.info(
        f"Created eval runbook {runbook.id} for book {book.id}, "
        f"score={total_score}, tier={recommendation_tier}, recommendation={recommendation}, "
        f"quality={tiered_quality_score}, strategic={tiered_strategic_fit_score}, "
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
