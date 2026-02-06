"""Wikidata portrait sync service for entity profiles.

Fetches entity portraits from Wikidata/Wikimedia Commons, resizes to 400x400 JPEG,
uploads to S3, and updates entity.image_url.

Fallback chain (when enabled):
  Wikidata SPARQL → Wikimedia Commons SDC → Google Knowledge Graph → NLS Historical Maps

Adapted from scripts/wikidata_portraits.py for app context (httpx, app S3/CDN).
"""

import io
import logging
import math
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

# Wikimedia Commons API endpoint (for SDC search)
COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"

# Google Knowledge Graph API endpoint
GOOGLE_KG_API_URL = "https://kgapi.googleapis.com/v1/entities:search"

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
# Each entity needs ~2s (1.5s rate limit + HTTP round-trip).
MAX_ENTITIES_PER_REQUEST = 10

# Lower cap when fallbacks are enabled (more HTTP calls per entity).
# Worst case per entity: 1.5s Wikidata + 1.5s Commons + Google KG + NLS ≈ 6-7s.
MAX_ENTITIES_WITH_FALLBACKS = 3

# Max entity IDs that can be passed in a single request
MAX_ENTITY_IDS = 50

# Statuses that trigger fallback providers
FALLBACK_TRIGGER_STATUSES = {"no_results", "below_threshold", "no_portrait"}

# Entity type to model mapping
ENTITY_MODELS = {
    "author": Author,
    "publisher": Publisher,
    "binder": Binder,
}

# NLS tile URL template for OS 6-inch 2nd edition maps
NLS_TILE_URL = "https://mapseries-tilesets.s3.amazonaws.com/os/6inch_2nd_ed/{z}/{x}/{y}.png"

# Google KG entity type mapping
GOOGLE_KG_TYPE_MAP = {
    "author": "Person",
    "publisher": "Organization",
    "binder": "Organization",
}


def _make_result(
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
    image_source: str | None = None,
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
        "image_source": image_source,
        "error": error,
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


def _download_image_direct(url: str) -> bytes | None:
    """Download image from any URL (not Wikimedia-specific)."""
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
        logger.exception("Failed to download image from %s", url)
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
        CacheControl="public, max-age=86400, stale-while-revalidate=3600",
    )
    return s3_key


def _build_cdn_url(s3_key: str) -> str:
    """Build CDN URL for an entity portrait S3 key."""
    cdn_base = get_cloudfront_cdn_url()
    return f"{cdn_base}/{s3_key}"


def _extract_qid_from_uri(wikidata_uri: str | None) -> str | None:
    """Extract QID (e.g. 'Q12345') from a full Wikidata URI.

    Example: 'http://www.wikidata.org/entity/Q5686' → 'Q5686'
    """
    if not wikidata_uri:
        return None
    parts = wikidata_uri.rstrip("/").rsplit("/", 1)
    if len(parts) == 2 and parts[1].startswith("Q"):
        return parts[1]
    return None


def _process_and_upload(
    db: Session,
    entity,
    entity_type: str,
    image_bytes: bytes,
    result: dict,
) -> dict:
    """Process image bytes and upload to S3, updating entity.image_url.

    Reusable core shared by Wikidata download and all fallback providers.
    """
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


def _download_process_upload(
    db: Session,
    entity,
    entity_type: str,
    best_candidate: dict,
    result: dict,
) -> dict:
    """Download from Wikimedia Commons, process, and upload portrait."""
    image_bytes = download_portrait(best_candidate["image_url"])
    if not image_bytes:
        result["status"] = "download_failed"
        return result

    return _process_and_upload(db, entity, entity_type, image_bytes, result)


# ---------------------------------------------------------------------------
# Fallback provider functions
# ---------------------------------------------------------------------------


def _search_commons_sdc(entity_name: str, wikidata_qid: str | None) -> str | None:
    """Search Wikimedia Commons using Structured Data (SDC).

    First tries SDC statement search (P180=QID, "depicts" property).
    Falls back to text search for "name portrait" if no QID or no results.

    Returns the first image file URL or None.
    """
    headers = {"User-Agent": USER_AGENT}

    # Strategy 1: SDC statement search with QID
    if wikidata_qid:
        try:
            params = {
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": f"haswbstatement:P180={wikidata_qid}",
                "gsrnamespace": "6",
                "gsrlimit": "5",
                "prop": "imageinfo",
                "iiprop": "url",
                "iiurlwidth": "400",
            }
            resp = httpx.get(COMMONS_API_URL, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                ii = page.get("imageinfo", [{}])[0]
                thumb = ii.get("thumburl") or ii.get("url")
                if thumb:
                    return thumb
        except httpx.HTTPError:
            logger.exception("Commons SDC search failed for QID %s", wikidata_qid)

    # Strategy 2: Text search fallback
    try:
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f"{entity_name} portrait",
            "gsrnamespace": "6",
            "gsrlimit": "3",
            "prop": "imageinfo",
            "iiprop": "url",
            "iiurlwidth": "400",
        }
        resp = httpx.get(COMMONS_API_URL, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            ii = page.get("imageinfo", [{}])[0]
            thumb = ii.get("thumburl") or ii.get("url")
            if thumb:
                return thumb
    except httpx.HTTPError:
        logger.exception("Commons text search failed for '%s'", entity_name)

    return None


def _search_google_kg(entity_name: str, entity_type: str) -> str | None:
    """Search Google Knowledge Graph for an entity image.

    Returns image.contentUrl from the first matching result, or None.
    Gracefully skips when API key is not configured.
    """
    settings = get_settings()
    if not settings.google_api_key:
        logger.debug("Google API key not configured, skipping KG search")
        return None

    kg_type = GOOGLE_KG_TYPE_MAP.get(entity_type, "Thing")
    try:
        params = {
            "query": entity_name,
            "key": settings.google_api_key,
            "types": kg_type,
            "limit": 3,
            "languages": "en",
        }
        resp = httpx.get(GOOGLE_KG_API_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        for element in data.get("itemListElement", []):
            result = element.get("result", {})
            image = result.get("image", {})
            content_url = image.get("contentUrl")
            if content_url:
                return content_url
    except httpx.HTTPError:
        logger.exception("Google KG search failed for '%s'", entity_name)

    return None


def _try_nls_fallback(
    db: Session,
    entity,
    entity_type: str,
    dry_run: bool,
) -> dict | None:
    """Try NLS historical map tile as portrait fallback.

    Only for publishers/binders. Uses Claude Haiku for location extraction
    and geopy for geocoding.

    Returns a result dict on success, or None if NLS is not applicable or fails.
    """
    if entity_type not in ("publisher", "binder"):
        return None

    # Optional imports — NLS needs anthropic and geopy
    try:
        import anthropic
        from geopy.geocoders import Nominatim
    except ImportError:
        logger.warning("anthropic or geopy not installed, skipping NLS fallback")
        return None

    # Get entity description from profile
    from app.models.entity_profile import EntityProfile

    description = None
    profile = (
        db.query(EntityProfile)
        .filter(
            EntityProfile.entity_type == entity_type,
            EntityProfile.entity_id == entity.id,
        )
        .first()
    )
    if profile and profile.bio_summary:
        description = profile.bio_summary

    # Step 1: Extract location via Claude Haiku
    import os

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set, skipping NLS fallback")
        return None

    import json

    try:
        client = anthropic.Anthropic(api_key=api_key)
        prompt = (
            "Extract the primary city or street address associated with this "
            "Victorian-era publisher or binder. "
            f"Entity name: {entity.name}. "
            f"Description: {description}. "
            'Return ONLY a JSON object: {"location": "street, city"} '
            'or {"location": null} if no location is mentioned.'
        )
        response = client.messages.create(
            model="claude-haiku-4-20250414",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        parsed = json.loads(text)
        location = parsed.get("location")
    except Exception:
        logger.exception("NLS location extraction failed for %s", entity.name)
        return None

    if not location:
        return None

    # Step 2: Geocode
    try:
        geocoder = Nominatim(user_agent=USER_AGENT)
        geo_result = geocoder.geocode(location, timeout=10)
        if geo_result is None:
            return None
        lat, lon = geo_result.latitude, geo_result.longitude
    except Exception:
        logger.exception("NLS geocoding failed for %s", location)
        return None

    # Step 3: Convert to tile coords
    zoom = 15
    n = 2**zoom
    x = int((lon + 180) / 360 * n)
    y = int(
        (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi)
        / 2
        * n
    )

    # Step 4: Download tile
    tile_url = NLS_TILE_URL.format(z=zoom, x=x, y=y)
    tile_bytes = _download_image_direct(tile_url)
    if not tile_bytes:
        return None

    result = _make_result(
        entity_type,
        entity.id,
        entity.name,
        "dry_run_match" if dry_run else "pending",
        image_source="nls_map",
    )
    result["location"] = location

    if dry_run:
        result["image_url_source"] = tile_url
        return result

    return _process_and_upload(db, entity, entity_type, tile_bytes, result)


def _try_fallback_providers(
    db: Session,
    entity,
    entity_type: str,
    result: dict,
    dry_run: bool,
    *,
    enable_commons: bool = True,
    enable_google: bool = True,
    enable_nls: bool = True,
) -> dict:
    """Try fallback providers in order after Wikidata miss.

    Chain: Commons SDC → Google KG → NLS Maps
    On first success: downloads, processes, uploads (unless dry_run).
    """
    wikidata_qid = _extract_qid_from_uri(result.get("wikidata_uri"))

    # --- Commons SDC ---
    if enable_commons:
        time.sleep(WIKIDATA_REQUEST_INTERVAL)  # Respect Wikimedia rate limit
        image_url = _search_commons_sdc(entity.name, wikidata_qid)
        if image_url:
            result["image_source"] = "commons_sdc"
            if dry_run:
                result["status"] = "dry_run_match"
                result["image_url_source"] = image_url
                return result
            image_bytes = _download_image_direct(image_url)
            if image_bytes:
                return _process_and_upload(db, entity, entity_type, image_bytes, result)

    # --- Google Knowledge Graph ---
    if enable_google:
        image_url = _search_google_kg(entity.name, entity_type)
        if image_url:
            result["image_source"] = "google_kg"
            if dry_run:
                result["status"] = "dry_run_match"
                result["image_url_source"] = image_url
                return result
            image_bytes = _download_image_direct(image_url)
            if image_bytes:
                return _process_and_upload(db, entity, entity_type, image_bytes, result)

    # --- NLS Historical Maps ---
    if enable_nls:
        nls_result = _try_nls_fallback(db, entity, entity_type, dry_run)
        if nls_result:
            return nls_result

    return result


def _maybe_fallback(
    db: Session,
    entity,
    entity_type: str,
    result: dict,
    dry_run: bool,
    enable_commons: bool,
    enable_google: bool,
    enable_nls: bool,
) -> dict:
    """Try fallback providers if any are enabled, otherwise return result as-is."""
    if any((enable_commons, enable_google, enable_nls)):
        return _try_fallback_providers(
            db,
            entity,
            entity_type,
            result,
            dry_run,
            enable_commons=enable_commons,
            enable_google=enable_google,
            enable_nls=enable_nls,
        )
    return result


def _finalize_wikidata_match(
    db: Session,
    entity,
    entity_type: str,
    best_candidate: dict,
    result: dict,
    dry_run: bool,
) -> dict:
    """Handle a successful Wikidata candidate match (with image)."""
    result["wikidata_uri"] = best_candidate["uri"]
    result["wikidata_label"] = best_candidate["label"]
    result["image_source"] = "wikidata"

    if dry_run:
        result["status"] = "dry_run_match"
        result["image_url_source"] = best_candidate["image_url"]
        return result

    return _download_process_upload(db, entity, entity_type, best_candidate, result)


def _process_person_entity(
    db: Session,
    entity,
    entity_type: str,
    threshold: float,
    dry_run: bool,
    *,
    enable_commons: bool = False,
    enable_google: bool = False,
    enable_nls: bool = False,
) -> dict:
    """Process a person entity (author)."""
    entity_name = entity.name
    entity_birth = getattr(entity, "birth_year", None)
    entity_death = getattr(entity, "death_year", None)
    book_titles = get_entity_book_titles(db, entity_type, entity.id)
    fb = {
        "enable_commons": enable_commons,
        "enable_google": enable_google,
        "enable_nls": enable_nls,
    }

    result = _make_result(entity_type, entity.id, entity_name, "no_results")

    sparql = build_sparql_query_person(entity_name)
    bindings = query_wikidata(sparql)

    if not bindings:
        return _maybe_fallback(db, entity, entity_type, result, dry_run, **fb)

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
        return _maybe_fallback(db, entity, entity_type, result, dry_run, **fb)

    result["wikidata_uri"] = best_candidate["uri"]
    result["wikidata_label"] = best_candidate["label"]

    if not best_candidate.get("image_url"):
        result["status"] = "no_portrait"
        return _maybe_fallback(db, entity, entity_type, result, dry_run, **fb)

    return _finalize_wikidata_match(db, entity, entity_type, best_candidate, result, dry_run)


def _process_org_entity(
    db: Session,
    entity,
    entity_type: str,
    threshold: float,
    dry_run: bool,
    *,
    enable_commons: bool = False,
    enable_google: bool = False,
    enable_nls: bool = False,
) -> dict:
    """Process an organizational entity (publisher or binder firm)."""
    fb = {
        "enable_commons": enable_commons,
        "enable_google": enable_google,
        "enable_nls": enable_nls,
    }
    result = _make_result(entity_type, entity.id, entity.name, "no_results")

    sparql = build_sparql_query_org(entity.name)
    bindings = query_wikidata(sparql)

    if not bindings:
        return _maybe_fallback(db, entity, entity_type, result, dry_run, **fb)

    grouped = group_sparql_results(bindings)
    best_candidate = None
    best_score = 0.0

    for _uri, candidate in grouped.items():
        ns = name_similarity(entity.name, candidate["label"])
        score = ns * 0.8 + (0.2 if candidate.get("image_url") else 0.0)

        if score > best_score:
            best_score = score
            best_candidate = candidate

    result["score"] = round(best_score, 4)

    if best_score < threshold or best_candidate is None:
        result["status"] = "below_threshold"
        return _maybe_fallback(db, entity, entity_type, result, dry_run, **fb)

    result["wikidata_uri"] = best_candidate["uri"]
    result["wikidata_label"] = best_candidate["label"]

    if not best_candidate.get("image_url"):
        result["status"] = "no_portrait"
        return _maybe_fallback(db, entity, entity_type, result, dry_run, **fb)

    return _finalize_wikidata_match(db, entity, entity_type, best_candidate, result, dry_run)


def run_portrait_sync(
    db: Session,
    dry_run: bool = True,
    threshold: float = 0.7,
    entity_type: str | None = None,
    entity_ids: list[int] | None = None,
    skip_existing: bool = True,
    enable_fallbacks: bool = False,
    skip_commons: bool = False,
    skip_google: bool = False,
    skip_nls: bool = False,
) -> dict:
    """Orchestrate portrait sync for all matching entities.

    Args:
        db: Database session.
        dry_run: If True, score candidates but don't download/upload.
        threshold: Minimum confidence score for a match.
        entity_type: Filter to a single entity type. Required when entity_ids is set.
        entity_ids: Filter to specific entity IDs (max 50).
        skip_existing: Skip entities that already have an image_url.
        enable_fallbacks: Enable fallback providers (Commons SDC, Google KG, NLS).
        skip_commons: Skip Wikimedia Commons SDC fallback.
        skip_google: Skip Google Knowledge Graph fallback.
        skip_nls: Skip NLS historical map fallback.

    Returns:
        Dict with 'results' list and 'summary' counters.

    Raises:
        ValueError: If entity_ids provided without entity_type, or if too many
            entities would be processed.
    """
    if entity_ids and not entity_type:
        msg = "entity_type is required when entity_ids is specified"
        raise ValueError(msg)

    if entity_ids and len(entity_ids) > MAX_ENTITY_IDS:
        msg = f"Maximum {MAX_ENTITY_IDS} entity_ids per request"
        raise ValueError(msg)

    # Derive per-provider flags
    enable_commons = enable_fallbacks and not skip_commons
    enable_google = enable_fallbacks and not skip_google
    enable_nls = enable_fallbacks and not skip_nls

    # Adjust max entities when fallbacks enabled
    max_entities = MAX_ENTITIES_WITH_FALLBACKS if enable_fallbacks else MAX_ENTITIES_PER_REQUEST

    results: list[dict] = []
    skipped_existing_count = 0
    to_process: list[tuple[str, object]] = []

    entity_types = [entity_type] if entity_type else ["author", "publisher", "binder"]

    for etype in entity_types:
        model = ENTITY_MODELS[etype]
        query = db.query(model)

        if entity_ids:
            query = query.filter(model.id.in_(entity_ids))

        entities = query.all()

        for entity in entities:
            if skip_existing and entity.image_url:
                skipped_existing_count += 1
                results.append(_make_result(etype, entity.id, entity.name, "skipped"))
            else:
                to_process.append((etype, entity))

    if len(to_process) > max_entities:
        msg = (
            f"Too many entities to process ({len(to_process)}). "
            f"Maximum {max_entities} per request"
            f"{' (reduced with fallbacks enabled)' if enable_fallbacks else ''}"
            f" due to API Gateway timeout. "
            f"Use entity_type and/or entity_ids to filter."
        )
        raise ValueError(msg)

    for i, (etype, entity) in enumerate(to_process):
        try:
            if etype in ("publisher", "binder"):
                result = _process_org_entity(
                    db,
                    entity,
                    etype,
                    threshold,
                    dry_run,
                    enable_commons=enable_commons,
                    enable_google=enable_google,
                    enable_nls=enable_nls,
                )
            else:
                result = _process_person_entity(
                    db,
                    entity,
                    etype,
                    threshold,
                    dry_run,
                    enable_commons=enable_commons,
                    enable_google=enable_google,
                    enable_nls=enable_nls,
                )
            results.append(result)
        except Exception:
            logger.exception("Unexpected error processing %s/%s", etype, entity.id)
            results.append(
                _make_result(
                    etype, entity.id, entity.name, "processing_failed", error="Unexpected error"
                )
            )

        if i < len(to_process) - 1:
            time.sleep(WIKIDATA_REQUEST_INTERVAL)

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
        "fallback_commons_sdc": sum(1 for r in results if r.get("image_source") == "commons_sdc"),
        "fallback_google_kg": sum(1 for r in results if r.get("image_source") == "google_kg"),
        "fallback_nls_map": sum(1 for r in results if r.get("image_source") == "nls_map"),
    }

    return {"results": results, "summary": summary}
