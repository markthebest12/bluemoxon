"""AI profile generation via AWS Bedrock Claude API."""

import json
import logging
import os
import random
import re
import time

from botocore.exceptions import ClientError

from app.services.bedrock import MODEL_IDS, get_bedrock_client, get_model_id

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "haiku"

MAX_RETRIES = 3
BASE_DELAY = 2.0


def _get_model_id() -> str:
    """Get Bedrock model ID from env var, falling back to default."""
    model_name = os.environ.get("ENTITY_PROFILE_MODEL", DEFAULT_MODEL)
    if model_name not in MODEL_IDS:
        logger.warning(
            "ENTITY_PROFILE_MODEL=%s not in MODEL_IDS, falling back to default (%s)",
            model_name,
            DEFAULT_MODEL,
        )
        model_name = DEFAULT_MODEL
    return get_model_id(model_name)


def _invoke(system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
    """Invoke Bedrock Claude with retry/backoff and return response text.

    Retries on ThrottlingException with exponential backoff matching
    the pattern in bedrock.invoke_bedrock().
    """
    client = get_bedrock_client()
    model_id = _get_model_id()
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
                modelId=model_id,
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
            if error_code == "ThrottlingException" and attempt < MAX_RETRIES:
                logger.warning("Bedrock throttled (attempt %d/%d)", attempt + 1, MAX_RETRIES + 1)
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


def generate_bio_and_stories(
    name: str,
    entity_type: str,
    birth_year: int | None = None,
    death_year: int | None = None,
    founded_year: int | None = None,
    book_titles: list[str] | None = None,
    connections: list[dict] | None = None,
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
        raw = _invoke(_BIO_SYSTEM_PROMPT, user_prompt, max_tokens=1024)
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
        return _invoke(_CONNECTION_SYSTEM_PROMPT, user_prompt, max_tokens=200).strip()
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
        raw = _invoke(_RELATIONSHIP_SYSTEM_PROMPT, user_prompt, max_tokens=1024)
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
