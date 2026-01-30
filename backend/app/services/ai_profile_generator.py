"""AI profile generation via Claude API."""

import json
import logging
import os

from anthropic import Anthropic

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-3-5-haiku-20241022"


def _get_model() -> str:
    """Get model from env var, falling back to default."""
    return os.environ.get("ENTITY_PROFILE_MODEL", DEFAULT_MODEL)


def _get_client() -> Anthropic:
    """Create Anthropic client. API key from ANTHROPIC_API_KEY env var."""
    return Anthropic()


def generate_bio_and_stories(
    name: str,
    entity_type: str,
    birth_year: int | None = None,
    death_year: int | None = None,
    founded_year: int | None = None,
    book_titles: list[str] | None = None,
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

    prompt = f"""You are a reference librarian and literary historian specializing in Victorian-era \
literature and publishing. You have deep knowledge of personal histories, scandals, relationships, \
and anecdotes of the period.

Given this entity from a rare book collection:
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
Be factual. Draw from commonly known historical record.
If the entity is obscure, provide what is known and note the obscurity."""

    try:
        client = _get_client()
        response = client.messages.create(
            model=_get_model(),
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        return json.loads(text)
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
) -> str | None:
    """Generate one-sentence narrative for a connection.

    Returns: narrative string or None on failure.
    """
    books_str = ", ".join(shared_book_titles) if shared_book_titles else "various works"

    prompt = f"""You are a reference librarian specializing in Victorian-era publishing networks.

Describe this connection in one sentence for a rare book collector:
  {entity1_name} ({entity1_type}) connected to {entity2_name} ({entity2_type})
  Connection: {connection_type}
  Shared works: {books_str}

Focus on why this connection matters in Victorian publishing history.
Be factual and concise. Return ONLY the single sentence, no quotes."""

    try:
        client = _get_client()
        response = client.messages.create(
            model=_get_model(),
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
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
) -> dict | None:
    """Generate full relationship story for high-impact connections.

    Returns: {"summary": str, "details": list[dict], "narrative_style": str} or None.
    """
    books_str = ", ".join(shared_book_titles) if shared_book_titles else "various works"

    prompt = f"""You are a literary historian with deep knowledge of Victorian-era personal \
relationships.

Given this connection between two entities in a rare book collection:
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

Return ONLY valid JSON: {{"summary": "...", "details": [...], "narrative_style": "..."}}
Be factual. Draw from commonly known historical record."""

    try:
        client = _get_client()
        response = client.messages.create(
            model=_get_model(),
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        return json.loads(text)
    except Exception:
        logger.exception(
            "Failed to generate relationship story for %s-%s",
            entity1_name,
            entity2_name,
        )
        return None
