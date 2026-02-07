"""Wikidata SPARQL client for entity portrait matching.

Handles SPARQL query construction, HTTP execution against the Wikidata
endpoint, rate limiting, and result parsing. Used by portrait_sync.py
for querying Wikidata candidate entities.
"""

import logging

import httpx

logger = logging.getLogger(__name__)

# Wikidata SPARQL endpoint
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"

# User-Agent required by Wikimedia API policy
USER_AGENT = "BlueMoxonBot/1.0 (https://bluemoxon.com; contact@bluemoxon.com)"

# Rate limiting: Wikidata requests min interval in seconds
WIKIDATA_REQUEST_INTERVAL = 1.5


class WikidataThrottledError(Exception):
    """Raised when Wikidata returns 429 or 503 — do not retry immediately."""


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
        if resp.status_code in (429, 503):
            logger.warning("Wikidata throttled (HTTP %s)", resp.status_code)
            raise WikidataThrottledError(f"Wikidata HTTP {resp.status_code}")
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", {}).get("bindings", [])
    except WikidataThrottledError:
        raise
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
