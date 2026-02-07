"""Wikidata portrait sync service for entity profiles.

Fetches entity portraits from Wikidata/Wikimedia Commons, resizes to 400x400 JPEG,
uploads to S3, and updates entity.image_url.

This is the canonical implementation for portrait sync logic. Both the admin API
endpoint and the CLI script (scripts/wikidata_portraits.py) delegate to this module.

SPARQL query building and Wikidata HTTP client live in wikidata_client.py.
Image download/process/upload pipeline lives in app.utils.image_processing.
"""

import logging
import re
import time

from sqlalchemy.orm import Session

from app.models import ENTITY_MODEL_MAP
from app.models.book import Book
from app.services.wikidata_client import (
    WIKIDATA_REQUEST_INTERVAL,
    WikidataThrottledError,  # noqa: F401 — referenced in docstrings as raised exception
    build_sparql_query_org,
    build_sparql_query_person,
    group_sparql_results,
    query_wikidata,
)
from app.utils.image_processing import (
    _download_process_upload,
    build_cdn_url,  # noqa: F401 — re-exported for consumers
    download_portrait,  # noqa: F401 — re-exported for consumers
    process_portrait,  # noqa: F401 — re-exported for consumers
    upload_to_s3,  # noqa: F401 — re-exported for consumers
)
from app.utils.wikidata_scoring import name_similarity, score_candidate

logger = logging.getLogger(__name__)

# Max entities per request to fit within API Gateway 30s timeout.
# Each entity needs ~2s (1.5s rate limit + HTTP round-trip), but
# publishers/binders may fire up to 3 queries (org + person fallback),
# each with 1.5s rate-limit sleep. Worst case per entity: ~7.5s.
# 5 entities × 7.5s = 37.5s — tight but within timeout with headroom
# for fast-path entities that hit on first query.
MAX_ENTITIES_PER_REQUEST = 5

# Max entity IDs that can be passed in a single request
MAX_ENTITY_IDS = 50

# Regex to strip common business suffixes for person-name extraction.
# Matches patterns like "& Son", "& Sons", "& Co.", "& Bros.", "and Company"
_BUSINESS_SUFFIXES_RE = re.compile(
    r",?\s*(?:&|and)\s+(?:Sons?|Co\.?|Company|Bros\.?|Brothers)\.?\s*$",
    re.IGNORECASE,
)


def make_result(
    entity_type: str,
    entity_id: int,
    entity_name: str,
    status: str,
    *,
    score: float = 0.0,
    wikidata_uri: str | None = None,
    wikidata_label: str | None = None,
    image_uploaded: bool = False,
    s3_key: str | None = None,
    cdn_url: str | None = None,
    image_url_source: str | None = None,
    error: str | None = None,
) -> dict:
    """Create a standardized result dict for a single entity."""
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "entity_name": entity_name,
        "status": status,
        "score": score,
        "wikidata_uri": wikidata_uri,
        "wikidata_label": wikidata_label,
        "image_uploaded": image_uploaded,
        "s3_key": s3_key,
        "cdn_url": cdn_url,
        "image_url_source": image_url_source,
        "error": error,
    }


def _extract_person_name(entity_name: str) -> str | None:
    """Strip common business suffixes to extract a potential founder name.

    Many Victorian publishers/binders are named after their founders
    (e.g. "Riviere & Son" -> "Riviere", "Edward Moxon and Co." -> "Edward Moxon").

    Returns the stripped name if different from original, else None.
    """
    stripped = _BUSINESS_SUFFIXES_RE.sub("", entity_name).strip().rstrip(",").strip()
    if stripped and stripped != entity_name:
        return stripped
    return None


def get_entity_book_titles(db: Session, entity_type: str, entity_id: int) -> list[str]:
    """Get book titles associated with an entity."""
    if entity_type == "author":
        books = db.query(Book.title).filter(Book.author_id == entity_id).all()
    elif entity_type == "publisher":
        books = db.query(Book.title).filter(Book.publisher_id == entity_id).all()
    elif entity_type == "binder":
        books = db.query(Book.title).filter(Book.binder_id == entity_id).all()
    else:
        return []
    return [b.title for b in books]


def process_person_entity(
    db: Session,
    entity,
    entity_type: str,
    threshold: float,
    dry_run: bool,
) -> dict:
    """Process a person entity (author or binder person).

    Queries Wikidata, scores candidates, optionally downloads and uploads portrait.

    Returns:
        Result dict with status, score, and optional upload details.
    """
    entity_name = entity.name
    entity_birth = getattr(entity, "birth_year", None)
    entity_death = getattr(entity, "death_year", None)

    # For binders, use founded_year/closed_year as rough year proxies
    if entity_type == "binder":
        entity_birth = getattr(entity, "founded_year", None)
        entity_death = getattr(entity, "closed_year", None)

    book_titles = get_entity_book_titles(db, entity_type, entity.id)

    result = make_result(entity_type, entity.id, entity_name, "no_results")

    sparql = build_sparql_query_person(entity_name)
    bindings = query_wikidata(sparql)

    if not bindings:
        return result

    candidates = group_sparql_results(bindings)
    best_score = 0.0
    best_candidate = None

    for _uri, candidate in candidates.items():
        score = score_candidate(
            entity_name=entity_name,
            entity_birth=entity_birth,
            entity_death=entity_death,
            entity_book_titles=book_titles,
            candidate_label=candidate["label"],
            candidate_birth=candidate["birth"],
            candidate_death=candidate["death"],
            candidate_works=candidate["works"],
            candidate_occupations=candidate["occupations"],
        )
        if score > best_score:
            best_score = score
            best_candidate = candidate

    result["score"] = round(best_score, 4)

    if best_score < threshold or best_candidate is None:
        result["status"] = "below_threshold"
        return result

    result["wikidata_uri"] = best_candidate["uri"]
    result["wikidata_label"] = best_candidate["label"]

    if not best_candidate.get("image_url"):
        result["status"] = "no_portrait"
        return result

    if dry_run:
        result["status"] = "dry_run_match"
        result["image_url_source"] = best_candidate["image_url"]
        return result

    return _download_process_upload(db, entity, entity_type, best_candidate, result)


def _try_person_sparql_fallback(entity_name: str) -> tuple[list[dict], str]:
    """Try person SPARQL queries as fallback for org entities.

    Many Victorian publishers/binders are named after their founders
    who exist on Wikidata as persons (Q5), not organizations.

    Tries the original name first, then strips business suffixes
    (e.g. "Riviere & Son" -> "Riviere", "Edward Moxon and Co." -> "Edward Moxon").

    Returns (bindings, match_source) tuple. match_source is one of:
    "person_exact", "person_stripped", or "" if no match.
    Raises WikidataThrottledError if Wikidata is rate-limiting.
    """
    # Rate-limit: caller already fired an org query, respect Wikidata interval
    time.sleep(WIKIDATA_REQUEST_INTERVAL)

    # Try original name as a person (e.g. "Bernard Quaritch")
    person_sparql = build_sparql_query_person(entity_name)
    bindings = query_wikidata(person_sparql)
    if bindings:
        logger.info(
            "Org SPARQL empty for '%s', found person match via exact name",
            entity_name,
        )
        return bindings, "person_exact"

    # Try with business suffixes stripped (e.g. "Edward Moxon and Co." -> "Edward Moxon")
    stripped_name = _extract_person_name(entity_name)
    if stripped_name and "," not in stripped_name:
        time.sleep(WIKIDATA_REQUEST_INTERVAL)
        person_sparql = build_sparql_query_person(stripped_name)
        bindings = query_wikidata(person_sparql)
        if bindings:
            logger.info(
                "Org SPARQL empty for '%s', found person match via stripped name '%s'",
                entity_name,
                stripped_name,
            )
            return bindings, "person_stripped"

    return [], ""


def process_org_entity(
    db: Session,
    entity,
    entity_type: str,
    threshold: float,
    dry_run: bool,
) -> dict:
    """Process an organizational entity (publisher or binder firm).

    Uses organization SPARQL query with name-similarity scoring.
    Falls back to person SPARQL when org query returns no results,
    since many Victorian publishers/binders are named after their
    founders who exist as persons on Wikidata.

    Returns:
        Result dict with status, score, and optional upload details.
    """
    result = make_result(entity_type, entity.id, entity.name, "no_results")
    match_source = "org"

    sparql = build_sparql_query_org(entity.name)
    bindings = query_wikidata(sparql)

    if not bindings:
        # Fallback: try person SPARQL — many Victorian publishers/binders
        # are named after their founders (e.g. "Bernard Quaritch",
        # "Edward Moxon and Co." -> "Edward Moxon").
        bindings, match_source = _try_person_sparql_fallback(entity.name)
        if not match_source:
            match_source = "org"  # keep default if no fallback match

    if not bindings:
        return result

    # Group results to handle multiple rows per entity
    grouped = group_sparql_results(bindings)
    best_candidate = None
    best_score = 0.0

    # Intentionally use org-style scoring (name + image bonus) even for
    # person-fallback results. Full score_candidate() is worse here because
    # publisher founded_year != founder birth_year, and publisher book
    # associations != Wikidata notable works. SPARQL exact-label matching
    # already constrains false positives sufficiently.
    # When fallback used stripped name, score against that name for accuracy.
    scoring_name = (
        _extract_person_name(entity.name) if match_source == "person_stripped" else entity.name
    )
    for _uri, candidate in grouped.items():
        ns = name_similarity(scoring_name or entity.name, candidate["label"])
        score = ns * 0.8 + (0.2 if candidate.get("image_url") else 0.0)

        if score > best_score:
            best_score = score
            best_candidate = candidate

    result["score"] = round(best_score, 4)
    result["match_source"] = match_source

    if best_score < threshold or best_candidate is None:
        result["status"] = "below_threshold"
        return result

    result["wikidata_uri"] = best_candidate["uri"]
    result["wikidata_label"] = best_candidate["label"]

    if not best_candidate.get("image_url"):
        result["status"] = "no_portrait"
        return result

    if dry_run:
        result["status"] = "dry_run_match"
        result["image_url_source"] = best_candidate["image_url"]
        return result

    return _download_process_upload(db, entity, entity_type, best_candidate, result)


def run_portrait_sync(
    db: Session,
    dry_run: bool = True,
    threshold: float = 0.7,
    entity_type: str | None = None,
    entity_ids: list[int] | None = None,
    skip_existing: bool = True,
) -> dict:
    """Orchestrate portrait sync for all matching entities.

    Args:
        db: Database session.
        dry_run: If True, score candidates but don't download/upload.
        threshold: Minimum confidence score for a match.
        entity_type: Filter to a single entity type. Required when entity_ids is set.
        entity_ids: Filter to specific entity IDs (max 50).
        skip_existing: Skip entities that already have an image_url.

    Returns:
        Dict with 'results' list and 'summary' counters.

    Raises:
        ValueError: If entity_ids provided without entity_type, or if too many
            entities would be processed (max 10 per request due to API Gateway timeout).
    """
    if entity_ids and not entity_type:
        msg = "entity_type is required when entity_ids is specified"
        raise ValueError(msg)

    if entity_ids and len(entity_ids) > MAX_ENTITY_IDS:
        msg = f"Maximum {MAX_ENTITY_IDS} entity_ids per request"
        raise ValueError(msg)

    results: list[dict] = []
    skipped_existing_count = 0
    to_process: list[tuple[str, object]] = []

    entity_types = [entity_type] if entity_type else ["author", "publisher", "binder"]

    # Collect entities to process, count skipped
    for etype in entity_types:
        model = ENTITY_MODEL_MAP[etype]
        query = db.query(model)

        if entity_ids:
            query = query.filter(model.id.in_(entity_ids))

        entities = query.all()

        for entity in entities:
            if skip_existing and entity.image_url:
                skipped_existing_count += 1
                results.append(make_result(etype, entity.id, entity.name, "skipped"))
            else:
                to_process.append((etype, entity))

    # Enforce per-request cap (API Gateway 30s timeout)
    if len(to_process) > MAX_ENTITIES_PER_REQUEST:
        msg = (
            f"Too many entities to process ({len(to_process)}). "
            f"Maximum {MAX_ENTITIES_PER_REQUEST} per request due to API Gateway timeout. "
            f"Use entity_type and/or entity_ids to filter."
        )
        raise ValueError(msg)

    # Process entities
    for i, (etype, entity) in enumerate(to_process):
        try:
            if etype in ("publisher", "binder"):
                result = process_org_entity(db, entity, etype, threshold, dry_run)
            else:
                result = process_person_entity(db, entity, etype, threshold, dry_run)
            results.append(result)
        except Exception:
            logger.exception("Unexpected error processing %s/%s", etype, entity.id)
            results.append(
                make_result(
                    etype, entity.id, entity.name, "processing_failed", error="Unexpected error"
                )
            )

        # Rate limit between Wikidata requests (skip after last entity)
        if i < len(to_process) - 1:
            time.sleep(WIKIDATA_REQUEST_INTERVAL)

    # Commit all DB changes at end (entity.image_url updates were flushed)
    if not dry_run:
        db.commit()

    summary = {
        "total_processed": len(results),
        "skipped_existing": skipped_existing_count,
        "matched": sum(1 for r in results if r["status"] in ("uploaded", "dry_run_match")),
        "uploaded": sum(1 for r in results if r["status"] == "uploaded"),
        "no_results": sum(1 for r in results if r["status"] == "no_results"),
        "below_threshold": sum(1 for r in results if r["status"] == "below_threshold"),
        "no_portrait": sum(1 for r in results if r["status"] == "no_portrait"),
        "download_failed": sum(1 for r in results if r["status"] == "download_failed"),
        "upload_failed": sum(1 for r in results if r["status"] == "upload_failed"),
        "processing_failed": sum(1 for r in results if r["status"] == "processing_failed"),
    }

    return {"results": results, "summary": summary}
