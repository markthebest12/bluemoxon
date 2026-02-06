"""Wikidata portrait sync service for entity profiles.

Fetches entity portraits from Wikidata/Wikimedia Commons, resizes to 400x400 JPEG,
uploads to S3, and updates entity.image_url.

Adapted from scripts/wikidata_portraits.py for app context (httpx, app S3/CDN).
"""

import io
import logging
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
from scripts.wikidata_scoring import name_similarity, score_candidate

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

# Entity type to model mapping
ENTITY_MODELS = {
    "author": Author,
    "publisher": Publisher,
    "binder": Binder,
}


def _escape_sparql_string(value: str) -> str:
    """Escape a value for use in a SPARQL string literal (double-quoted)."""
    return (
        value.replace("\\", "\\\\")
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
    """Execute SPARQL query against Wikidata and return results."""
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
    """Extract filename from Wikimedia Commons URL."""
    if "Special:FilePath/" in url:
        return url.split("Special:FilePath/")[-1]
    return url.rsplit("/", 1)[-1]


def group_sparql_results(bindings: list[dict]) -> dict[str, dict]:
    """Group SPARQL result bindings by Wikidata item URI.

    Wikidata returns one row per (item, occupation, work) combination,
    so we need to collapse them into one record per item.
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
    """Download portrait image from Wikimedia Commons."""
    filename = extract_filename_from_commons_url(image_url)
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
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img = ImageOps.exif_transpose(img)
            if img.mode in ("RGBA", "P", "LA"):
                img = img.convert("RGB")
            img.thumbnail(PORTRAIT_SIZE, Image.Resampling.LANCZOS)
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
    )
    return s3_key


def _build_cdn_url(s3_key: str) -> str:
    """Build CDN URL for an entity portrait S3 key."""
    cdn_base = get_cloudfront_cdn_url()
    return f"{cdn_base}/{s3_key}"


def _process_person_entity(
    db: Session,
    entity,
    entity_type: str,
    threshold: float,
    dry_run: bool,
) -> dict:
    """Process a person entity (author or binder)."""
    entity_name = entity.name
    entity_birth = getattr(entity, "birth_year", None)
    entity_death = getattr(entity, "death_year", None)

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
        "wikidata_label": None,
        "image_uploaded": False,
        "s3_key": None,
        "cdn_url": None,
        "image_url_source": None,
        "error": None,
    }

    sparql = build_sparql_query_person(entity_name)
    bindings = query_wikidata(sparql)

    if not bindings:
        result["status"] = "no_results"
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
        cdn_url = _build_cdn_url(s3_key)

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


def _process_publisher_entity(
    db: Session,
    entity: Publisher,
    threshold: float,
    dry_run: bool,
) -> dict:
    """Process a publisher entity (organizational search)."""
    result = {
        "entity_type": "publisher",
        "entity_id": entity.id,
        "entity_name": entity.name,
        "status": "no_match",
        "score": 0.0,
        "wikidata_uri": None,
        "wikidata_label": None,
        "image_uploaded": False,
        "s3_key": None,
        "cdn_url": None,
        "image_url_source": None,
        "error": None,
    }

    sparql = build_sparql_query_org(entity.name)
    bindings = query_wikidata(sparql)

    if not bindings:
        result["status"] = "no_results"
        return result

    best_candidate = None
    best_score = 0.0

    for row in bindings:
        label = row.get("itemLabel", {}).get("value", "")
        image_url = row.get("image", {}).get("value")

        ns = name_similarity(entity.name, label)
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
    result["wikidata_label"] = best_candidate["label"]

    if not best_candidate.get("image_url"):
        result["status"] = "no_portrait"
        return result

    if dry_run:
        result["status"] = "dry_run_match"
        result["image_url_source"] = best_candidate["image_url"]
        return result

    image_bytes = download_portrait(best_candidate["image_url"])
    if not image_bytes:
        result["status"] = "download_failed"
        return result

    processed = process_portrait(image_bytes)
    if not processed:
        result["status"] = "processing_failed"
        return result

    try:
        s3_key = upload_to_s3(processed, "publisher", entity.id)
        cdn_url = _build_cdn_url(s3_key)

        entity.image_url = cdn_url
        db.flush()

        result["status"] = "uploaded"
        result["image_uploaded"] = True
        result["s3_key"] = s3_key
        result["cdn_url"] = cdn_url
    except Exception:
        logger.exception("S3 upload failed for publisher/%s", entity.id)
        result["status"] = "upload_failed"
        result["error"] = "S3 upload failed"

    return result


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
        entity_type: Filter to a single entity type.
        entity_ids: Filter to specific entity IDs.
        skip_existing: Skip entities that already have an image_url.

    Returns:
        Dict with 'results' list and 'summary' counters.
    """
    results: list[dict] = []
    skipped_existing = 0

    entity_types = [entity_type] if entity_type else ["author", "publisher", "binder"]

    for etype in entity_types:
        model = ENTITY_MODELS[etype]
        query = db.query(model)

        if entity_ids:
            query = query.filter(model.id.in_(entity_ids))

        entities = query.all()
        logger.info("Processing %d %ss", len(entities), etype)

        for entity in entities:
            if skip_existing and entity.image_url:
                skipped_existing += 1
                results.append(
                    {
                        "entity_type": etype,
                        "entity_id": entity.id,
                        "entity_name": entity.name,
                        "status": "skipped",
                        "score": 0.0,
                        "wikidata_uri": None,
                        "wikidata_label": None,
                        "image_uploaded": False,
                        "s3_key": None,
                        "cdn_url": None,
                        "image_url_source": None,
                        "error": None,
                    }
                )
                continue

            try:
                if etype == "publisher":
                    result = _process_publisher_entity(db, entity, threshold, dry_run)
                else:
                    result = _process_person_entity(db, entity, etype, threshold, dry_run)
                results.append(result)
            except Exception:
                logger.exception("Unexpected error processing %s/%s", etype, entity.id)
                results.append(
                    {
                        "entity_type": etype,
                        "entity_id": entity.id,
                        "entity_name": entity.name,
                        "status": "processing_failed",
                        "score": 0.0,
                        "wikidata_uri": None,
                        "wikidata_label": None,
                        "image_uploaded": False,
                        "s3_key": None,
                        "cdn_url": None,
                        "image_url_source": None,
                        "error": "Unexpected error",
                    }
                )

            time.sleep(WIKIDATA_REQUEST_INTERVAL)

    # Commit all DB changes at end (entity.image_url updates were flushed)
    if not dry_run:
        db.commit()

    summary = {
        "total_processed": len(results),
        "skipped_existing": skipped_existing,
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
