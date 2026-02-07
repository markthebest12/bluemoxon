"""Wikidata portrait sync service for entity profiles.

Fetches entity portraits from Wikidata/Wikimedia Commons, resizes to 400x400 JPEG,
uploads to S3, and updates entity.image_url.

This is the canonical implementation for portrait sync logic. Both the admin API
endpoint and the CLI script (scripts/wikidata_portraits.py) delegate to this module.
"""

import io
import logging
import re
import time
from urllib.parse import quote, unquote

import httpx
from PIL import Image, ImageOps
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.author import Author
from app.models.binder import Binder
from app.models.book import Book
from app.models.publisher import Publisher
from app.services.aws_clients import get_s3_client
from app.utils.cdn import get_cloudfront_cdn_url
from app.utils.wikidata_scoring import name_similarity, score_candidate

logger = logging.getLogger(__name__)

# Wikidata SPARQL endpoint
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"

# Wikimedia Commons file URL template (400px wide)
COMMONS_FILE_URL = "https://commons.wikimedia.org/wiki/Special:FilePath/{filename}?width=400"

# Portrait dimensions and quality
PORTRAIT_SIZE = (400, 400)
PORTRAIT_QUALITY = 85

# S3 prefix for entity portraits
S3_ENTITIES_PREFIX = "entities/"

# Rate limiting: Wikidata requests min interval in seconds
WIKIDATA_REQUEST_INTERVAL = 1.5

# User-Agent required by Wikimedia API policy
USER_AGENT = "BlueMoxonBot/1.0 (https://bluemoxon.com; contact@bluemoxon.com)"

# Max entities per request to fit within API Gateway 30s timeout.
# Each entity needs ~2s (1.5s rate limit + HTTP round-trip), but
# publishers/binders may fire up to 3 queries (org + person fallback).
# For publisher-heavy batches, use smaller batches or entity_ids.
MAX_ENTITIES_PER_REQUEST = 10

# Max entity IDs that can be passed in a single request
MAX_ENTITY_IDS = 50

# Regex to strip common business suffixes for person-name extraction.
# Matches patterns like "& Son", "& Sons", "& Co.", "and Co."
_BUSINESS_SUFFIXES_RE = re.compile(
    r",?\s*(?:&|and)\s+(?:Sons?|Co\.?|Company)\.?\s*$",
    re.IGNORECASE,
)

# Entity type to model mapping
ENTITY_MODELS = {
    "author": Author,
    "publisher": Publisher,
    "binder": Binder,
}


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


def _escape_sparql_string(value: str) -> str:
    """Escape a value for use in a SPARQL string literal (double-quoted).

    Handles backslashes, double quotes, newlines, carriage returns, and tabs
    per the SPARQL 1.1 grammar for STRING_LITERAL2 (double-quoted strings).
    """
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def _extract_person_name(entity_name: str) -> str | None:
    """Strip common business suffixes to extract a potential founder name.

    Many Victorian publishers/binders are named after their founders
    (e.g. "Rivière & Son" → "Rivière", "Edward Moxon and Co." → "Edward Moxon").

    Returns the stripped name if different from original, else None.
    """
    stripped = _BUSINESS_SUFFIXES_RE.sub("", entity_name).strip().rstrip(",").strip()
    if stripped and stripped != entity_name:
        return stripped
    return None


def build_sparql_query_person(entity_name: str) -> str:
    """Build SPARQL query for a human entity (author, binder person)."""
    escaped_name = _escape_sparql_string(entity_name)
    return f"""
SELECT ?item ?itemLabel ?itemDescription ?birth ?death
       ?image ?occupation ?occupationLabel ?work ?workLabel
WHERE {{
  ?item rdfs:label "{escaped_name}"@en .
  ?item wdt:P31 wd:Q5 .
  OPTIONAL {{ ?item wdt:P569 ?birth . }}
  OPTIONAL {{ ?item wdt:P570 ?death . }}
  OPTIONAL {{ ?item wdt:P18 ?image . }}
  OPTIONAL {{
    ?item wdt:P106 ?occupation .
    ?occupation rdfs:label ?occupationLabel .
    FILTER(LANG(?occupationLabel) = "en")
  }}
  OPTIONAL {{
    ?item wdt:P800 ?work .
    ?work rdfs:label ?workLabel .
    FILTER(LANG(?workLabel) = "en")
  }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}}
LIMIT 10
"""


def build_sparql_query_org(entity_name: str) -> str:
    """Build SPARQL query for an organizational entity (publisher, binder firm)."""
    escaped_name = _escape_sparql_string(entity_name)
    return f"""
SELECT ?item ?itemLabel ?itemDescription ?image ?inception
WHERE {{
  ?item rdfs:label "{escaped_name}"@en .
  {{ ?item wdt:P31 wd:Q2085381 . }}
  UNION
  {{ ?item wdt:P31 wd:Q7275 . }}
  UNION
  {{ ?item wdt:P31 wd:Q4830453 . }}
  OPTIONAL {{ ?item wdt:P18 ?image . }}
  OPTIONAL {{ ?item wdt:P571 ?inception . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
}}
LIMIT 10
"""


def query_wikidata(sparql: str) -> list[dict]:
    """Execute SPARQL query against Wikidata and return results.

    Returns list of result bindings (dicts).
    """
    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": USER_AGENT,
    }
    try:
        resp = httpx.get(
            WIKIDATA_SPARQL_URL,
            params={"query": sparql},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", {}).get("bindings", [])
    except httpx.HTTPError:
        logger.exception("Wikidata SPARQL query failed")
        return []


def parse_year_from_datetime(dt_str: str | None) -> int | None:
    """Extract year from Wikidata datetime string (e.g. '1812-02-07T00:00:00Z')."""
    if not dt_str:
        return None
    try:
        return int(dt_str[:4])
    except (ValueError, IndexError):
        return None


def extract_filename_from_commons_url(url: str) -> str:
    """Extract filename from Wikimedia Commons URL.

    Example: 'http://commons.wikimedia.org/wiki/Special:FilePath/Charles_Dickens.jpg'
    -> 'Charles_Dickens.jpg'
    """
    if "Special:FilePath/" in url:
        return url.split("Special:FilePath/")[-1]
    # Fallback: last path segment
    return url.rsplit("/", 1)[-1]


def group_sparql_results(bindings: list[dict]) -> dict[str, dict]:
    """Group SPARQL result bindings by Wikidata item URI.

    Wikidata returns one row per (item, occupation, work) combination,
    so we need to collapse them into one record per item.

    Returns dict keyed by item URI with aggregated fields.
    """
    grouped: dict[str, dict] = {}
    for row in bindings:
        item_uri = row.get("item", {}).get("value", "")
        if not item_uri:
            continue

        if item_uri not in grouped:
            grouped[item_uri] = {
                "uri": item_uri,
                "label": row.get("itemLabel", {}).get("value", ""),
                "description": row.get("itemDescription", {}).get("value", ""),
                "birth": parse_year_from_datetime(row.get("birth", {}).get("value")),
                "death": parse_year_from_datetime(row.get("death", {}).get("value")),
                "image_url": row.get("image", {}).get("value"),
                "occupations": set(),
                "works": set(),
            }

        occ_label = row.get("occupationLabel", {}).get("value")
        if occ_label:
            grouped[item_uri]["occupations"].add(occ_label)

        work_label = row.get("workLabel", {}).get("value")
        if work_label:
            grouped[item_uri]["works"].add(work_label)

    # Convert sets to lists for downstream use
    for item in grouped.values():
        item["occupations"] = list(item["occupations"])
        item["works"] = list(item["works"])

    return grouped


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


def download_portrait(image_url: str) -> bytes | None:
    """Download portrait image from Wikimedia Commons.

    Args:
        image_url: Full Wikimedia Commons image URL.

    Returns:
        Image bytes or None on failure.
    """
    filename = extract_filename_from_commons_url(image_url)
    # Decode first to avoid double-encoding (Wikidata returns pre-encoded URLs)
    url = COMMONS_FILE_URL.format(filename=quote(unquote(filename), safe=""))

    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=30,
            follow_redirects=True,
        )
        resp.raise_for_status()
        return resp.content
    except httpx.HTTPError:
        logger.exception("Failed to download portrait from %s", url)
        return None


def process_portrait(image_bytes: bytes) -> bytes | None:
    """Resize portrait to 400x400 JPEG.

    Maintains aspect ratio via thumbnail, converts to RGB, applies EXIF rotation.

    Returns:
        JPEG bytes or None on failure.
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            # Apply EXIF orientation
            img = ImageOps.exif_transpose(img)

            # Convert to RGB if necessary
            if img.mode in ("RGBA", "P", "LA"):
                img = img.convert("RGB")

            # Resize maintaining aspect ratio
            img.thumbnail(PORTRAIT_SIZE, Image.Resampling.LANCZOS)

            # Save to bytes
            output = io.BytesIO()
            img.save(output, "JPEG", quality=PORTRAIT_QUALITY, optimize=True)
            return output.getvalue()
    except Exception:
        logger.exception("Failed to process portrait image")
        return None


def upload_to_s3(image_bytes: bytes, entity_type: str, entity_id: int) -> str:
    """Upload portrait JPEG to S3. Returns the S3 key."""
    settings = get_settings()
    s3 = get_s3_client()
    s3_key = f"{S3_ENTITIES_PREFIX}{entity_type}/{entity_id}/portrait.jpg"

    s3.put_object(
        Bucket=settings.images_bucket,
        Key=s3_key,
        Body=image_bytes,
        ContentType="image/jpeg",
        CacheControl="public, max-age=86400, stale-while-revalidate=3600",
    )
    return s3_key


def build_cdn_url(s3_key: str) -> str:
    """Build CDN URL for an entity portrait S3 key."""
    cdn_base = get_cloudfront_cdn_url()
    return f"{cdn_base}/{s3_key}"


def _download_process_upload(
    db: Session,
    entity,
    entity_type: str,
    best_candidate: dict,
    result: dict,
) -> dict:
    """Download, process, and upload portrait for a matched candidate.

    Shared pipeline for both person and publisher entities.
    """
    image_bytes = download_portrait(best_candidate["image_url"])
    if not image_bytes:
        result["status"] = "download_failed"
        return result

    processed = process_portrait(image_bytes)
    if not processed:
        result["status"] = "processing_failed"
        return result

    try:
        s3_key = upload_to_s3(processed, entity_type, entity.id)
        cdn_url = build_cdn_url(s3_key)

        entity.image_url = cdn_url
        db.flush()

        result["status"] = "uploaded"
        result["image_uploaded"] = True
        result["s3_key"] = s3_key
        result["cdn_url"] = cdn_url
    except Exception:
        logger.exception("S3 upload failed for %s/%s", entity_type, entity.id)
        result["status"] = "upload_failed"
        result["error"] = "S3 upload failed"

    return result


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


def _try_person_sparql_fallback(entity_name: str) -> list[dict]:
    """Try person SPARQL queries as fallback for org entities.

    Many Victorian publishers/binders are named after their founders
    who exist on Wikidata as persons (Q5), not organizations.

    Tries the original name first, then strips business suffixes
    (e.g. "Rivière & Son" → "Rivière", "Edward Moxon and Co." → "Edward Moxon").

    Returns SPARQL bindings list (may be empty).
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
        return bindings

    # Try with business suffixes stripped (e.g. "Edward Moxon and Co." → "Edward Moxon")
    stripped_name = _extract_person_name(entity_name)
    if stripped_name:
        time.sleep(WIKIDATA_REQUEST_INTERVAL)
        person_sparql = build_sparql_query_person(stripped_name)
        bindings = query_wikidata(person_sparql)
        if bindings:
            logger.info(
                "Org SPARQL empty for '%s', found person match via stripped name '%s'",
                entity_name,
                stripped_name,
            )
            return bindings

    return []


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

    sparql = build_sparql_query_org(entity.name)
    bindings = query_wikidata(sparql)

    if not bindings:
        # Fallback: try person SPARQL — many Victorian publishers/binders
        # are named after their founders (e.g. "Bernard Quaritch",
        # "Edward Moxon and Co." → "Edward Moxon").
        bindings = _try_person_sparql_fallback(entity.name)

    if not bindings:
        return result

    # Group results to handle multiple rows per entity
    grouped = group_sparql_results(bindings)
    best_candidate = None
    best_score = 0.0

    # Intentionally use org-style scoring (name + image bonus) even for
    # person-fallback results. Full score_candidate() is worse here because
    # publisher founded_year ≠ founder birth_year, and publisher book
    # associations ≠ Wikidata notable works. SPARQL exact-label matching
    # already constrains false positives sufficiently.
    for _uri, candidate in grouped.items():
        ns = name_similarity(entity.name, candidate["label"])
        score = ns * 0.8 + (0.2 if candidate.get("image_url") else 0.0)

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
        model = ENTITY_MODELS[etype]
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
