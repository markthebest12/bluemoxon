"""NLS historical map tile fallback for entity portraits.

When the Wikidata portrait pipeline fails to find a match for publishers or binders,
this module falls back to using National Library of Scotland (NLS) historical OS map
tiles as portrait images, based on the entity's location.

Pipeline:
1. Extract location from entity name/description using Claude Haiku
2. Geocode location to lat/lon using geopy/Nominatim
3. Convert to OSM tile coordinates
4. Download historical OS 6-inch 2nd edition map tile from NLS
5. Process and upload to S3 as entity portrait
"""

import json
import logging
import math
import os
from datetime import UTC, datetime

import anthropic
import requests
from geopy.geocoders import Nominatim

from scripts.wikidata_portraits import (
    get_cdn_url,
    process_portrait,
    upload_to_s3,
)

logger = logging.getLogger(__name__)

# Lazy singleton for Anthropic client — avoids creating a new instance per call
_anthropic_client: anthropic.Anthropic | None = None


def _get_anthropic_client() -> anthropic.Anthropic | None:
    """Return a shared Anthropic client, creating it on first use.

    Returns None (with a warning) when ANTHROPIC_API_KEY is not set.
    """
    global _anthropic_client  # noqa: PLW0603
    if _anthropic_client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set, skipping location extraction")
            return None
        _anthropic_client = anthropic.Anthropic(api_key=api_key)
    return _anthropic_client


# NLS tile URL template for OS 6-inch 2nd edition maps
NLS_TILE_URL = "https://mapseries-tilesets.s3.amazonaws.com/os/6inch_2nd_ed/{z}/{x}/{y}.png"

# User-Agent for HTTP requests
USER_AGENT = "BlueMoxonBot/1.0"


def extract_location(entity_name: str, entity_description: str | None) -> str | None:
    """Extract the primary location from an entity using Claude Haiku.

    Args:
        entity_name: Name of the publisher or binder.
        entity_description: Optional bio_summary or description text.

    Returns:
        Location string (e.g. "Albemarle Street, London") or None.
    """
    client = _get_anthropic_client()
    if client is None:
        return None

    try:
        prompt = (
            "Extract the primary city or street address associated with this "
            "Victorian-era publisher or binder. "
            f"Entity name: {entity_name}. "
            f"Description: {entity_description}. "
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
        return parsed.get("location")
    except Exception:
        logger.exception("Failed to extract location for %s", entity_name)
        return None


def geocode_location(location: str) -> tuple[float, float] | None:
    """Geocode a location string to lat/lon coordinates.

    Args:
        location: Human-readable location (e.g. "Albemarle Street, London").

    Returns:
        (latitude, longitude) tuple or None on failure.
    """
    try:
        geocoder = Nominatim(user_agent=USER_AGENT)
        result = geocoder.geocode(location, timeout=10)
        if result is None:
            return None
        return (result.latitude, result.longitude)
    except Exception:
        logger.exception("Geocoding failed for %s", location)
        return None


def latlon_to_tile(lat: float, lon: float, zoom: int = 15) -> tuple[int, int, int]:
    """Convert lat/lon to OSM tile coordinates at the given zoom level.

    Args:
        lat: Latitude in degrees.
        lon: Longitude in degrees.
        zoom: Zoom level (default 15).

    Returns:
        (zoom, x, y) tile coordinate tuple.
    """
    n = 2**zoom
    x = int((lon + 180) / 360 * n)
    y = int(
        (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi)
        / 2
        * n
    )
    return (zoom, x, y)


def download_nls_tile(zoom: int, x: int, y: int) -> bytes | None:
    """Download a historical OS map tile from NLS.

    Args:
        zoom: Tile zoom level.
        x: Tile x coordinate.
        y: Tile y coordinate.

    Returns:
        PNG image bytes or None on failure.
    """
    url = NLS_TILE_URL.format(z=zoom, x=x, y=y)
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.content
    except Exception:
        logger.exception("Failed to download NLS tile from %s", url)
        return None


def process_nls_fallback(
    db,
    entity,
    entity_type: str,
    dry_run: bool,
    settings,
) -> dict:
    """Process NLS map fallback for a single entity.

    Orchestrates location extraction, geocoding, tile download, and upload.

    Args:
        db: SQLAlchemy session.
        entity: Publisher or Binder model instance.
        entity_type: "publisher" or "binder".
        dry_run: If True, skip upload step.
        settings: App settings (for S3 bucket/CDN).

    Returns:
        Result dict with status, location, etc.
    """
    from app.models.entity_profile import EntityProfile

    result = {
        "entity_type": entity_type,
        "entity_id": entity.id,
        "entity_name": entity.name,
        "status": "pending",
        "image_source": "nls_map",
        "location": None,
        "image_uploaded": False,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    # Get entity description from entity_profiles table
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

    # Step 1: Extract location
    location = extract_location(entity.name, description)
    if not location:
        result["status"] = "no_location"
        return result

    result["location"] = location

    # Step 2: Geocode
    coords = geocode_location(location)
    if not coords:
        result["status"] = "geocode_failed"
        return result

    lat, lon = coords

    # Step 3: Convert to tile coordinates
    z, x, y = latlon_to_tile(lat, lon)

    # Step 4: Download tile
    tile_bytes = download_nls_tile(z, x, y)
    if not tile_bytes:
        result["status"] = "tile_download_failed"
        return result

    # Dry run: stop before upload
    if dry_run:
        result["status"] = "dry_run"
        return result

    # Step 5: Process image (resize to portrait format)
    processed = process_portrait(tile_bytes)
    if not processed:
        result["status"] = "processing_failed"
        return result

    # Step 6: Upload to S3
    try:
        s3_key = upload_to_s3(processed, entity_type, entity.id, settings)
        cdn_url = get_cdn_url(s3_key, settings)

        # Update entity image_url
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
