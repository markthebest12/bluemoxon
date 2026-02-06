"""Wikidata portrait matching pipeline for entity profiles.

Batch script that:
1. Queries all authors, publishers, and binders from the database
2. Searches Wikidata SPARQL for matching entities
3. Scores candidates using confidence scoring (name, year, works, occupation)
4. Downloads portrait images from Wikimedia Commons for high-confidence matches
5. Resizes and uploads to S3 as entity profile portraits

Prerequisites:
    - Direct database access (connects via DATABASE_URL / BMX_DATABASE_URL)
    - AWS credentials for S3 uploads (BMX_S3_BUCKET or environment defaults)
    - The --env flag sets BMX_ENVIRONMENT but does NOT configure remote DB access;
      you need either a local database, an SSH tunnel, or to run from an EC2 instance
      that can reach the RDS endpoint.

Usage (from an environment with DB access):
    cd backend && poetry run python -m scripts.wikidata_portraits --env staging --dry-run
    cd backend && poetry run python -m scripts.wikidata_portraits --env staging --threshold 0.8
    cd backend && poetry run python -m scripts.wikidata_portraits --env staging --entity-type author
    cd backend && poetry run python -m scripts.wikidata_portraits --env staging --entity-type author --entity-id 31 --entity-id 227

Fallback providers (for entities unmatched by Wikidata):
    cd backend && poetry run python -m scripts.wikidata_portraits --env staging --enable-fallbacks
    cd backend && poetry run python -m scripts.wikidata_portraits --env staging --skip-nls --skip-google

Alternative — Admin API endpoint (no DB access required, but limited to 10 entities/request):
    bmx-api POST '/admin/maintenance/portrait-sync?dry_run=true&entity_type=author&entity_ids=1'
    bmx-api POST '/admin/maintenance/portrait-sync?dry_run=false&entity_type=author&entity_ids=1,2,3'
    bmx-api POST '/admin/maintenance/portrait-sync?entity_type=publisher&entity_ids=1,2,3,4,5'

Output:
    JSON lines to stdout (one per entity), summary to stderr.
    Pipe to jq for filtering: ... | jq 'select(.status == "uploaded")'

Rate limiting:
    1.5s between Wikidata requests (WIKIDATA_REQUEST_INTERVAL).
    Full batch (140 authors + 91 publishers + 22 binders) takes ~6-7 minutes.
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
from app.services.portrait_sync import (
    build_sparql_query_org,
    build_sparql_query_person,
    extract_filename_from_commons_url,
    group_sparql_results,
    prepare_name_variants,
)
from app.utils.wikidata_scoring import score_candidate

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
    name_variants = prepare_name_variants(entity_name, entity_type)
    sparql = build_sparql_query_person(name_variants)
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
    name_variants = prepare_name_variants(entity.name, "publisher")
    sparql = build_sparql_query_org(name_variants)
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
        from app.utils.wikidata_scoring import name_similarity

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
        "--enable-fallbacks",
        action="store_true",
        help="Enable all fallback providers (Commons SDC, Google KG, NLS) for unmatched entities",
    )
    parser.add_argument(
        "--skip-nls",
        action="store_true",
        help="Skip NLS historical map fallback for unmatched publishers/binders",
    )
    parser.add_argument(
        "--skip-commons",
        action="store_true",
        help="Skip Wikimedia Commons SDC fallback",
    )
    parser.add_argument(
        "--skip-google",
        action="store_true",
        help="Skip Google Knowledge Graph fallback",
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

            # Fallback providers for unmatched entities
            enable_any_fallback = args.enable_fallbacks or (
                not args.skip_nls and etype in ("publisher", "binder")
            )
            if enable_any_fallback:
                from app.services.portrait_sync import (
                    FALLBACK_TRIGGER_STATUSES,
                    _try_fallback_providers,
                )

                enable_commons = args.enable_fallbacks and not args.skip_commons
                enable_google = args.enable_fallbacks and not args.skip_google
                enable_nls = not args.skip_nls

                unmatched = [
                    r
                    for r in results
                    if r["entity_type"] == etype and r["status"] in FALLBACK_TRIGGER_STATUSES
                ]
                if unmatched:
                    logger.info(
                        "Running fallback providers for %d unmatched %ss",
                        len(unmatched),
                        etype,
                    )
                    unmatched_ids = {r["entity_id"] for r in unmatched}
                    model_cls = {"author": Author, "publisher": Publisher, "binder": Binder}[etype]
                    fb_entities = db.query(model_cls).filter(model_cls.id.in_(unmatched_ids)).all()
                    entity_to_result = {r["entity_id"]: r for r in unmatched}

                    for fb_entity in fb_entities:
                        original_result = entity_to_result[fb_entity.id]
                        fb_result = _try_fallback_providers(
                            db,
                            fb_entity,
                            etype,
                            original_result,
                            args.dry_run,
                            enable_commons=enable_commons,
                            enable_google=enable_google,
                            enable_nls=enable_nls,
                        )
                        if fb_result.get("image_source"):
                            results.append(fb_result)
                            print(json.dumps(fb_result))

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
