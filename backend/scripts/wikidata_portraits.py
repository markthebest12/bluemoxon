"""Wikidata portrait matching pipeline for entity profiles.

Batch script that:
1. Queries all authors, publishers, and binders from the database
2. Searches Wikidata SPARQL for matching entities
3. Scores candidates using confidence scoring (name, year, works, occupation)
4. Downloads portrait images from Wikimedia Commons for high-confidence matches
5. Resizes and uploads to S3 as entity profile portraits

Usage:
    cd backend && poetry run python -m scripts.wikidata_portraits --env staging --dry-run
    cd backend && poetry run python -m scripts.wikidata_portraits --env staging --threshold 0.8
    cd backend && poetry run python -m scripts.wikidata_portraits --env staging --entity-type author
    cd backend && poetry run python -m scripts.wikidata_portraits --env staging --entity-type author --entity-id 31 --entity-id 227
"""

# ruff: noqa: T201

import argparse
import io
import json
import logging
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote, unquote

import requests
from PIL import Image, ImageOps

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.db import SessionLocal
from app.models.author import Author
from app.models.binder import Binder
from app.models.book import Book
from app.models.publisher import Publisher
from app.services.aws_clients import get_s3_client
from scripts.wikidata_scoring import score_candidate

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

logger = logging.getLogger(__name__)


def _escape_sparql_string(value: str) -> str:
    """Escape a value for use in a SPARQL string literal (double-quoted).

    Handles backslashes, double quotes, newlines, carriage returns, and tabs
    per the SPARQL 1.1 grammar for STRING_LITERAL2 (double-quoted strings).
    """
    return (
        value.replace("\\", "\\\\")  # Backslash first
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


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
    """Build SPARQL query for an organizational entity (publisher)."""
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
        resp = requests.get(
            WIKIDATA_SPARQL_URL,
            params={"query": sparql},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", {}).get("bindings", [])
    except requests.RequestException:
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

    Example: 'http://commons.wikimedia.org/wiki/Special:FilePath/Charles_Dickens_-_Project_Gutenberg_eText_13103.jpg'
    -> 'Charles_Dickens_-_Project_Gutenberg_eText_13103.jpg'
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
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.content
    except requests.RequestException:
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


def upload_to_s3(
    image_bytes: bytes,
    entity_type: str,
    entity_id: int,
    settings,
) -> str:
    """Upload portrait JPEG to S3.

    Args:
        image_bytes: Processed JPEG bytes.
        entity_type: 'author', 'publisher', or 'binder'.
        entity_id: Database ID of the entity.
        settings: App settings (for bucket name).

    Returns:
        S3 key for the uploaded object.
    """
    s3 = get_s3_client()
    s3_key = f"{S3_ENTITIES_PREFIX}{entity_type}/{entity_id}/portrait.jpg"

    s3.put_object(
        Bucket=settings.images_bucket,
        Key=s3_key,
        Body=image_bytes,
        ContentType="image/jpeg",
    )

    return s3_key


def get_entity_book_titles(db, entity_type: str, entity_id: int) -> list[str]:
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


def get_cdn_url(s3_key: str, settings) -> str:
    """Build CDN URL for an S3 key."""
    if settings.images_cdn_url:
        return f"{settings.images_cdn_url}/{s3_key}"
    if settings.images_cdn_domain:
        return f"https://{settings.images_cdn_domain}/{s3_key}"
    return f"https://app.bluemoxon.com/book-images/{s3_key}"


def process_person_entity(
    db,
    entity,
    entity_type: str,
    threshold: float,
    dry_run: bool,
    settings,
) -> dict:
    """Process a person entity (author or binder person).

    Queries Wikidata, scores candidates, optionally downloads and uploads portrait.

    Returns:
        Result dict for JSON-lines output.
    """
    entity_name = entity.name
    entity_birth = getattr(entity, "birth_year", None)
    entity_death = getattr(entity, "death_year", None)

    # For binders, use founded_year as rough birth proxy
    if entity_type == "binder":
        entity_birth = getattr(entity, "founded_year", None)
        entity_death = getattr(entity, "closed_year", None)

    book_titles = get_entity_book_titles(db, entity_type, entity.id)

    result = {
        "entity_type": entity_type,
        "entity_id": entity.id,
        "entity_name": entity_name,
        "status": "no_match",
        "score": 0.0,
        "wikidata_uri": None,
        "image_uploaded": False,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    # Query Wikidata
    sparql = build_sparql_query_person(entity_name)
    bindings = query_wikidata(sparql)

    if not bindings:
        result["status"] = "no_results"
        return result

    # Group and score candidates
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

    # Check for portrait image
    if not best_candidate.get("image_url"):
        result["status"] = "no_portrait"
        return result

    if dry_run:
        result["status"] = "dry_run_match"
        result["image_url_source"] = best_candidate["image_url"]
        return result

    # Download and process portrait
    image_bytes = download_portrait(best_candidate["image_url"])
    if not image_bytes:
        result["status"] = "download_failed"
        return result

    processed = process_portrait(image_bytes)
    if not processed:
        result["status"] = "processing_failed"
        return result

    # Upload to S3
    try:
        s3_key = upload_to_s3(processed, entity_type, entity.id, settings)
        cdn_url = get_cdn_url(s3_key, settings)

        # Update entity image_url in database if the model has that field
        # (currently none of the models have image_url, so this is future-proofing)
        if hasattr(entity, "image_url"):
            entity.image_url = cdn_url
            db.commit()

        result["status"] = "uploaded"
        result["image_uploaded"] = True
        result["s3_key"] = s3_key
        result["cdn_url"] = cdn_url
    except Exception:
        logger.exception("S3 upload failed for %s/%s", entity_type, entity.id)
        result["status"] = "upload_failed"

    return result


def process_publisher_entity(
    db,
    entity: Publisher,
    threshold: float,
    dry_run: bool,
    settings,
) -> dict:
    """Process a publisher entity (organizational search).

    Uses organization SPARQL query instead of person query.

    Returns:
        Result dict for JSON-lines output.
    """
    result = {
        "entity_type": "publisher",
        "entity_id": entity.id,
        "entity_name": entity.name,
        "status": "no_match",
        "score": 0.0,
        "wikidata_uri": None,
        "image_uploaded": False,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    # Query Wikidata for organizational entities
    sparql = build_sparql_query_org(entity.name)
    bindings = query_wikidata(sparql)

    if not bindings:
        result["status"] = "no_results"
        return result

    # For publishers, we do a simpler name-based match
    # since organizations don't have birth/death years in the same way
    best_candidate = None
    best_score = 0.0

    for row in bindings:
        label = row.get("itemLabel", {}).get("value", "")
        image_url = row.get("image", {}).get("value")

        # Simple name similarity check for organizations
        from scripts.wikidata_scoring import name_similarity

        ns = name_similarity(entity.name, label)
        # Boost if has image
        score = ns * 0.8 + (0.2 if image_url else 0.0)

        if score > best_score:
            best_score = score
            best_candidate = {
                "uri": row.get("item", {}).get("value", ""),
                "label": label,
                "image_url": image_url,
            }

    result["score"] = round(best_score, 4)

    if best_score < threshold or best_candidate is None:
        result["status"] = "below_threshold"
        return result

    result["wikidata_uri"] = best_candidate["uri"]

    if not best_candidate.get("image_url"):
        result["status"] = "no_portrait"
        return result

    if dry_run:
        result["status"] = "dry_run_match"
        result["image_url_source"] = best_candidate["image_url"]
        return result

    # Download and process portrait
    image_bytes = download_portrait(best_candidate["image_url"])
    if not image_bytes:
        result["status"] = "download_failed"
        return result

    processed = process_portrait(image_bytes)
    if not processed:
        result["status"] = "processing_failed"
        return result

    # Upload to S3
    try:
        s3_key = upload_to_s3(processed, "publisher", entity.id, settings)
        cdn_url = get_cdn_url(s3_key, settings)

        if hasattr(entity, "image_url"):
            entity.image_url = cdn_url
            db.commit()

        result["status"] = "uploaded"
        result["image_uploaded"] = True
        result["s3_key"] = s3_key
        result["cdn_url"] = cdn_url
    except Exception:
        logger.exception("S3 upload failed for publisher/%s", entity.id)
        result["status"] = "upload_failed"

    return result


def main():
    """Main entry point for the Wikidata portrait pipeline."""
    parser = argparse.ArgumentParser(
        description="Wikidata portrait matching pipeline for entity profiles."
    )
    parser.add_argument(
        "--env",
        choices=["staging", "production"],
        default="staging",
        help="Target environment (default: staging)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Score candidates but don't download/upload images",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.7,
        help="Minimum confidence score for a match (default: 0.7)",
    )
    parser.add_argument(
        "--entity-type",
        choices=["author", "publisher", "binder"],
        help="Process only this entity type (default: all)",
    )
    parser.add_argument(
        "--entity-id",
        type=int,
        action="append",
        help="Process only this entity ID (requires --entity-type). Can be repeated.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--skip-nls",
        action="store_true",
        help="Skip NLS historical map fallback for unmatched publishers/binders",
    )

    args = parser.parse_args()

    if args.entity_id and not args.entity_type:
        parser.error("--entity-id requires --entity-type")

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    # Set environment before loading settings
    os.environ.setdefault("BMX_ENVIRONMENT", args.env)

    settings = get_settings()
    db = SessionLocal()

    try:
        results = []
        entity_types = [args.entity_type] if args.entity_type else ["author", "publisher", "binder"]

        for etype in entity_types:
            if etype == "author":
                query = db.query(Author)
                if args.entity_id:
                    query = query.filter(Author.id.in_(args.entity_id))
                entities = query.all()
                logger.info("Processing %d authors", len(entities))
                for entity in entities:
                    result = process_person_entity(
                        db, entity, "author", args.threshold, args.dry_run, settings
                    )
                    results.append(result)
                    # Output JSON-line immediately
                    print(json.dumps(result))
                    time.sleep(WIKIDATA_REQUEST_INTERVAL)

            elif etype == "publisher":
                query = db.query(Publisher)
                if args.entity_id:
                    query = query.filter(Publisher.id.in_(args.entity_id))
                entities = query.all()
                logger.info("Processing %d publishers", len(entities))
                for entity in entities:
                    result = process_publisher_entity(
                        db, entity, args.threshold, args.dry_run, settings
                    )
                    results.append(result)
                    print(json.dumps(result))
                    time.sleep(WIKIDATA_REQUEST_INTERVAL)

            elif etype == "binder":
                query = db.query(Binder)
                if args.entity_id:
                    query = query.filter(Binder.id.in_(args.entity_id))
                entities = query.all()
                logger.info("Processing %d binders", len(entities))
                for entity in entities:
                    result = process_person_entity(
                        db, entity, "binder", args.threshold, args.dry_run, settings
                    )
                    results.append(result)
                    print(json.dumps(result))
                    time.sleep(WIKIDATA_REQUEST_INTERVAL)

            # NLS map fallback for unmatched publishers/binders
            if not args.skip_nls and etype in ("publisher", "binder"):
                unmatched_statuses = {"no_results", "below_threshold", "no_portrait"}
                unmatched = [
                    r
                    for r in results
                    if r["entity_type"] == etype and r["status"] in unmatched_statuses
                ]
                if unmatched:
                    logger.info(
                        "Running NLS map fallback for %d unmatched %ss",
                        len(unmatched),
                        etype,
                    )
                    from scripts.nls_map_fallback import process_nls_fallback

                    # Build lookup of unmatched entity IDs
                    unmatched_ids = {r["entity_id"] for r in unmatched}

                    # Re-query entities for unmatched IDs
                    model_cls = Publisher if etype == "publisher" else Binder
                    nls_entities = db.query(model_cls).filter(model_cls.id.in_(unmatched_ids)).all()

                    for nls_entity in nls_entities:
                        nls_result = process_nls_fallback(
                            db, nls_entity, etype, args.dry_run, settings
                        )
                        results.append(nls_result)
                        print(json.dumps(nls_result))

        # Summary to stderr
        total = len(results)
        uploaded = sum(1 for r in results if r["image_uploaded"])
        matched = sum(1 for r in results if r["score"] >= args.threshold)
        logger.info(
            "Pipeline complete: %d entities processed, %d matched (>= %.2f), %d portraits uploaded",
            total,
            matched,
            args.threshold,
            uploaded,
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()
