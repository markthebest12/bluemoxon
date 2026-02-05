"""AI profile generation via AWS Bedrock Claude API."""

import json
import logging
import os
import random
import re
import time
from dataclasses import dataclass

from botocore.exceptions import ClientError
from sqlalchemy.orm import Session

from app.services.bedrock import MODEL_IDS, RETRYABLE_ERROR_CODES, get_bedrock_client, get_model_id

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "haiku"

MAX_RETRIES = 3
BASE_DELAY = 2.0


def _resolve_model_id(db: Session) -> str:
    """Resolve the Bedrock model ID for entity profile generation.

    Resolution order:
      1. app_config 'model.entity_profiles' (from DB, cached)
      2. ENTITY_PROFILE_MODEL env var
      3. DEFAULT_MODEL constant ('haiku')
    """
    # Lazy import to avoid circular dependency: app_config → models → ...
    from app.services.app_config import get_config

    model_name = None
    try:
        model_name = get_config(db, "model.entity_profiles")
    except Exception:
        logger.warning("Failed to read model config from DB, falling back to env/default")
    if not model_name:
        model_name = os.environ.get("ENTITY_PROFILE_MODEL", DEFAULT_MODEL)
    if model_name not in MODEL_IDS:
        logger.warning(
            "Entity profile model '%s' not in MODEL_IDS, falling back to default (%s)",
            model_name,
            DEFAULT_MODEL,
        )
        model_name = DEFAULT_MODEL
    return get_model_id(model_name)


@dataclass(frozen=True)
class GeneratorConfig:
    """Configuration resolved once per profile generation."""

    model_id: str

    @classmethod
    def resolve(cls, db: Session) -> "GeneratorConfig":
        """Resolve config from DB / env / default."""
        return cls(model_id=_resolve_model_id(db))


def _invoke(
    system_prompt: str, user_prompt: str, max_tokens: int = 1024, *, config: GeneratorConfig
) -> str:
    """Invoke Bedrock Claude with retry/backoff and return response text.

    Retries on transient Bedrock errors with exponential backoff matching
    the pattern in bedrock.invoke_bedrock().
    """
    client = get_bedrock_client()
    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
    )

    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            if attempt > 0:
                delay = BASE_DELAY * (2**attempt) + random.uniform(0, 1)  # noqa: S311
                logger.info("Bedrock profile retry %d/%d after %.1fs", attempt, MAX_RETRIES, delay)
                time.sleep(delay)

            response = client.invoke_model(
                modelId=config.model_id,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            response_body = json.loads(response["body"].read())
            content = response_body.get("content")
            if not content:
                raise ValueError("Empty content in Bedrock response")
            return content[0]["text"]

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code in RETRYABLE_ERROR_CODES and attempt < MAX_RETRIES:
                logger.warning(
                    "Bedrock %s (attempt %d/%d)", error_code, attempt + 1, MAX_RETRIES + 1
                )
                last_error = e
                continue
            raise

    raise last_error  # type: ignore[misc]


def _strip_markdown_fences(text: str) -> str:
    """Strip markdown code fences from LLM output before JSON parsing."""
    stripped = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    stripped = re.sub(r"\n?```\s*$", "", stripped)
    return stripped.strip()


def _format_connection_instructions(connections: list[dict] | None) -> str:
    """Format entity cross-link instructions for AI prompts."""
    if not connections:
        return ""
    conn_lines = "\n".join(
        f'- {c["entity_type"]}:{c["entity_id"]} "{c["name"]}"' for c in connections
    )
    return f"""

When mentioning any of these connected entities by name, wrap them in markers like this:
{{{{entity:author:32|Robert Browning}}}}

Connection list (ONLY use markers for entities in this list — never invent IDs):
{conn_lines}"""


_ENTITY_MARKER_RE = re.compile(r"\{\{entity:(\w+):(\d+)\|([^}]+)\}\}")


def strip_invalid_markers(text: str, valid_entity_ids: set[str]) -> str:
    """Strip entity markers whose IDs are not in the valid set.

    Valid markers are preserved. Invalid markers are replaced with just
    the display name (graceful degradation).
    """

    def _replace(match: re.Match) -> str:
        entity_type = match.group(1)
        entity_id = match.group(2)
        display_name = match.group(3)
        key = f"{entity_type}:{entity_id}"
        if key in valid_entity_ids:
            return match.group(0)  # preserve valid marker
        return display_name  # strip to plain text

    return _ENTITY_MARKER_RE.sub(_replace, text)


_BIO_SYSTEM_PROMPT = (
    "You are a reference librarian and literary historian specializing in Victorian-era "
    "literature and publishing. You have deep knowledge of personal histories, scandals, "
    "relationships, and anecdotes of the period. "
    "Return ONLY valid JSON. Be factual. Draw from commonly known historical record."
)

_CONNECTION_SYSTEM_PROMPT = (
    "You are a reference librarian specializing in Victorian-era publishing networks. "
    "Focus on why connections matter in Victorian publishing history. "
    "Be factual and concise."
)

_RELATIONSHIP_SYSTEM_PROMPT = (
    "You are a literary historian with deep knowledge of Victorian-era personal relationships. "
    "Be factual. Draw from commonly known historical record. Return ONLY valid JSON."
)

_DISCOVERY_SYSTEM_PROMPT = (
    "You are a literary historian specializing in Victorian-era personal relationships. "
    "You identify connections between authors, publishers, and binders that go beyond "
    "professional publishing ties — marriages, friendships, feuds, mentorships, and scandals. "
    "Be factual. Only report well-documented historical connections. Return ONLY valid JSON."
)

# Valid AI-discovered connection types (must match ConnectionType enum values)
_VALID_AI_CONNECTION_TYPES = frozenset(
    {"family", "friendship", "influence", "collaboration", "scandal"}
)

# Maximum AI connections per entity to prevent LLM hallucination bloat
_MAX_AI_CONNECTIONS = 10


def generate_ai_connections(
    entity_name: str,
    entity_type: str,
    entity_id: int,
    all_entities: list[dict],
    *,
    config: GeneratorConfig,
) -> list[dict]:
    """Discover personal connections between this entity and others in the collection.

    Args:
        entity_name: Name of the entity to discover connections for.
        entity_type: Type of entity (author, publisher, binder).
        entity_id: Database ID of the entity.
        all_entities: List of all collection entities as dicts with keys:
            entity_type, entity_id, name.
        config: Generator config with resolved model_id.

    Returns:
        List of validated connection dicts, each with:
            source_type, source_id, target_type, target_id,
            relationship, sub_type, confidence, evidence.
    """
    if not all_entities:
        return []

    entity_lines = "\n".join(
        f'- {e["entity_type"]}:{e["entity_id"]} "{e["name"]}"' for e in all_entities
    )

    user_prompt = f"""Given this entity from a Victorian rare book collection:
  Name: {entity_name}
  Type: {entity_type}
  ID: {entity_id}

And these other entities in the same collection:
{entity_lines}

Identify any PERSONAL connections between {entity_name} and the other entities listed above.
Only include connections you are confident are historically documented.

Connection types (use exactly these values):
- family: Marriage, siblings, parent-child, in-laws
- friendship: Close personal friends, social circle members
- influence: Mentorship, intellectual influence, inspiration
- collaboration: Co-authorship, literary partnerships, joint ventures
- scandal: Affairs, feuds, public controversies, legal disputes

For each connection, provide:
- target_type: The entity type from the list (author, publisher, binder)
- target_id: The entity ID number from the list
- relationship: One of: family, friendship, influence, collaboration, scandal
- sub_type: Specific relationship (e.g., "MARRIAGE", "MENTOR", "RIVALS", "CO-AUTHORS")
- confidence: 0.0 to 1.0 (1.0 = certain, 0.5 = likely, below 0.3 = rumored)
- evidence: One sentence explaining the connection

Return ONLY valid JSON: {{"connections": [...]}}
If no personal connections are known, return: {{"connections": []}}"""

    try:
        raw = _invoke(_DISCOVERY_SYSTEM_PROMPT, user_prompt, max_tokens=2048, config=config)
        text = _strip_markdown_fences(raw)
        result = json.loads(text)
        if not isinstance(result, dict) or not isinstance(result.get("connections"), list):
            logger.warning(
                "AI returned invalid shape for connections of %s:%d", entity_type, entity_id
            )
            return []

        all_entity_ids = {f"{e['entity_type']}:{e['entity_id']}" for e in all_entities}
        return _validate_ai_connections(
            result["connections"], entity_type, entity_id, all_entity_ids
        )
    except Exception:
        logger.exception("Failed to generate AI connections for %s %s", entity_type, entity_name)
        return []


def _validate_ai_connections(
    raw_connections: list,
    source_type: str,
    source_id: int,
    all_entity_ids: set[str],
) -> list[dict]:
    """Validate and clean AI-discovered connections.

    Filters out:
    - Self-connections (source == target)
    - Invalid relationship types
    - Targets not in the collection
    - Duplicates (same source+target+relationship)

    Returns cleaned list of connection dicts.
    """
    seen: set[str] = set()
    validated: list[dict] = []

    for conn in raw_connections:
        if len(validated) >= _MAX_AI_CONNECTIONS:
            break

        if not isinstance(conn, dict):
            continue

        target_type = conn.get("target_type")
        target_id = conn.get("target_id")
        relationship = conn.get("relationship")

        # Skip if missing required fields
        if not all([target_type, target_id is not None, relationship]):
            continue

        # Coerce target_id to int
        try:
            target_id = int(target_id)
        except (ValueError, TypeError):
            continue

        # Skip invalid relationship types
        if relationship not in _VALID_AI_CONNECTION_TYPES:
            continue

        # Skip self-connections
        if target_type == source_type and target_id == source_id:
            continue

        # Skip targets not in collection
        target_key = f"{target_type}:{target_id}"
        if target_key not in all_entity_ids:
            continue

        # Dedup by canonical key (lower ID first)
        source_key = f"{source_type}:{source_id}"
        pair = tuple(sorted([source_key, target_key]))
        dedup_key = f"{pair[0]}:{pair[1]}:{relationship}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        # Clamp confidence
        confidence = conn.get("confidence", 0.5)
        try:
            confidence = max(0.0, min(1.0, float(confidence)))
        except (ValueError, TypeError):
            confidence = 0.5

        raw_sub_type = conn.get("sub_type")
        sub_type = raw_sub_type.upper().strip() if isinstance(raw_sub_type, str) else raw_sub_type

        validated.append(
            {
                "source_type": source_type,
                "source_id": source_id,
                "target_type": target_type,
                "target_id": target_id,
                "relationship": relationship,
                "sub_type": sub_type,
                "confidence": confidence,
                "evidence": conn.get("evidence"),
            }
        )

    return validated


def generate_bio_and_stories(
    name: str,
    entity_type: str,
    birth_year: int | None = None,
    death_year: int | None = None,
    founded_year: int | None = None,
    book_titles: list[str] | None = None,
    connections: list[dict] | None = None,
    *,
    config: GeneratorConfig,
) -> dict:
    """Generate bio summary and personal stories for an entity.

    Returns: {"biography": str, "personal_stories": list[dict]}
    """
    dates_line = ""
    if birth_year and death_year:
        dates_line = f"Dates: {birth_year} - {death_year}"
    elif founded_year:
        dates_line = f"Founded: {founded_year}"

    book_list = ", ".join(book_titles) if book_titles else "None in collection"

    user_prompt = f"""Given this entity from a rare book collection:
  Name: {name}
  Type: {entity_type}
  {dates_line}
  Books in collection: {book_list}

Provide:

1. BIOGRAPHY: A 2-3 sentence biographical summary focusing on their significance in Victorian \
literary/publishing history.

2. PERSONAL_STORIES: An array of biographical facts — the "gossip" that makes this figure come \
alive. Include personal drama, scandals, tragedies, triumphs, and notable anecdotes. Each fact \
should have:
   - text: The story (1-2 sentences)
   - year: When it happened (if known, otherwise null)
   - significance: "revelation" (surprising/impactful), "notable" (interesting), or "context" \
(background)
   - tone: "dramatic", "scandalous", "tragic", "intellectual", or "triumphant"

Return ONLY valid JSON: {{"biography": "...", "personal_stories": [...]}}
If the entity is obscure, provide what is known and note the obscurity.{_format_connection_instructions(connections)}"""

    try:
        raw = _invoke(_BIO_SYSTEM_PROMPT, user_prompt, max_tokens=1024, config=config)
        text = _strip_markdown_fences(raw)
        result = json.loads(text)
        # Validate expected shape — must have biography string and personal_stories list
        if not isinstance(result, dict):
            logger.warning("LLM returned non-dict for %s %s: %s", entity_type, name, type(result))
            return {"biography": None, "personal_stories": []}
        if "biography" not in result:
            result["biography"] = None
        if not isinstance(result.get("personal_stories"), list):
            result["personal_stories"] = []
        return result
    except Exception:
        logger.exception("Failed to generate bio for %s %s", entity_type, name)
        return {"biography": None, "personal_stories": []}


def generate_connection_narrative(
    entity1_name: str,
    entity1_type: str,
    entity2_name: str,
    entity2_type: str,
    connection_type: str,
    shared_book_titles: list[str],
    connections: list[dict] | None = None,
    *,
    config: GeneratorConfig,
) -> str | None:
    """Generate one-sentence narrative for a connection.

    Returns: narrative string or None on failure.
    """
    books_str = ", ".join(shared_book_titles) if shared_book_titles else "various works"
    conn_instructions = _format_connection_instructions(connections)

    user_prompt = f"""Describe this connection in one sentence for a rare book collector:
  {entity1_name} ({entity1_type}) connected to {entity2_name} ({entity2_type})
  Connection: {connection_type}
  Shared works: {books_str}{conn_instructions}

Return ONLY the single sentence, no quotes."""

    try:
        return _invoke(
            _CONNECTION_SYSTEM_PROMPT, user_prompt, max_tokens=200, config=config
        ).strip()
    except Exception:
        logger.exception("Failed to generate narrative for %s-%s", entity1_name, entity2_name)
        return None


def generate_relationship_story(
    entity1_name: str,
    entity1_type: str,
    entity1_dates: str,
    entity2_name: str,
    entity2_type: str,
    entity2_dates: str,
    connection_type: str,
    shared_book_titles: list[str],
    trigger_type: str,
    connections: list[dict] | None = None,
    *,
    config: GeneratorConfig,
) -> dict | None:
    """Generate full relationship story for high-impact connections.

    Returns: {"summary": str, "details": list[dict], "narrative_style": str} or None.
    """
    books_str = ", ".join(shared_book_titles) if shared_book_titles else "various works"
    conn_instructions = _format_connection_instructions(connections)

    user_prompt = f"""Given this connection between two entities in a rare book collection:
  Entity 1: {entity1_name} ({entity1_type}, {entity1_dates})
  Entity 2: {entity2_name} ({entity2_type}, {entity2_dates})
  Connection type: {connection_type}
  Shared works: {books_str}
  Narrative trigger: {trigger_type}

Provide the relationship story:

1. SUMMARY: One-line summary of the relationship (for card display)

2. DETAILS: Array of biographical facts about this specific relationship.
   Each fact: {{"text": "...", "year": null_or_int, "significance": "revelation|notable|context", \
"tone": "dramatic|scandalous|tragic|intellectual|triumphant"}}
   Focus on personal anecdotes, dramatic events, and the human story.

3. NARRATIVE_STYLE: "prose-paragraph" for dramatic stories, "bullet-facts" for factual \
relationships, "timeline-events" for long-spanning connections.

Return ONLY valid JSON: {{"summary": "...", "details": [...], "narrative_style": "..."}}{conn_instructions}"""

    try:
        raw = _invoke(_RELATIONSHIP_SYSTEM_PROMPT, user_prompt, max_tokens=1024, config=config)
        text = _strip_markdown_fences(raw)
        result = json.loads(text)
        if not isinstance(result, dict) or "summary" not in result:
            logger.warning("LLM returned invalid shape for %s-%s", entity1_name, entity2_name)
            return None
        if not isinstance(result.get("details"), list):
            result["details"] = []
        return result
    except Exception:
        logger.exception(
            "Failed to generate relationship story for %s-%s",
            entity1_name,
            entity2_name,
        )
        return None
