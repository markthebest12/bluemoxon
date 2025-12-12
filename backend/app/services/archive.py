"""Wayback Machine archive service."""

import logging
from typing import TypedDict

import httpx

logger = logging.getLogger(__name__)

WAYBACK_SAVE_URL = "https://web.archive.org/save"
WAYBACK_AVAILABILITY_URL = "https://archive.org/wayback/available"
TIMEOUT_SECONDS = 30


class ArchiveResult(TypedDict):
    status: str  # "success", "failed", "pending"
    archived_url: str | None
    error: str | None


async def archive_url(url: str) -> ArchiveResult:
    """
    Archive a URL to the Wayback Machine.

    Args:
        url: The URL to archive

    Returns:
        ArchiveResult with status and archived_url or error
    """
    if not url:
        return {"status": "failed", "archived_url": None, "error": "No URL provided"}

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            # Request archive save
            save_url = f"{WAYBACK_SAVE_URL}/{url}"
            response = await client.get(save_url, follow_redirects=True)

            if response.status_code == 200:
                # Extract archived URL from response
                # Wayback returns Content-Location header with the archived path
                content_location = response.headers.get("Content-Location", "")
                if content_location:
                    archived_url = f"https://web.archive.org{content_location}"
                else:
                    # Fallback: construct from response URL
                    archived_url = str(response.url)

                logger.info(f"Successfully archived {url} to {archived_url}")
                return {
                    "status": "success",
                    "archived_url": archived_url,
                    "error": None,
                }
            else:
                error_msg = f"Wayback returned {response.status_code}: {response.text[:200]}"
                logger.warning(f"Failed to archive {url}: {error_msg}")
                return {
                    "status": "failed",
                    "archived_url": None,
                    "error": error_msg,
                }

    except httpx.TimeoutException:
        error_msg = f"Timeout after {TIMEOUT_SECONDS}s archiving {url}"
        logger.warning(error_msg)
        return {"status": "failed", "archived_url": None, "error": error_msg}

    except Exception as e:
        error_msg = f"Error archiving {url}: {str(e)}"
        logger.error(error_msg)
        return {"status": "failed", "archived_url": None, "error": error_msg}


async def check_archive_availability(url: str) -> dict:
    """
    Check if a URL is already archived in Wayback Machine.

    Args:
        url: The URL to check

    Returns:
        Dict with availability info
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                WAYBACK_AVAILABILITY_URL,
                params={"url": url},
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("archived_snapshots", {})
            return {}
    except Exception as e:
        logger.warning(f"Error checking availability for {url}: {e}")
        return {}
