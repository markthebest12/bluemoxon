"""Entity enrichment worker -- populates entity metadata via Bedrock.

Processes SQS messages triggered by entity creation (author, publisher, binder).
Uses Bedrock Haiku to research and populate birth/death years, founded/closed years,
era, and other metadata fields that are critical for portrait sync scoring.

Only updates fields that are currently NULL to avoid overwriting user-provided data.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from botocore.exceptions import ClientError

from app.db import SessionLocal
from app.models.author import Author
from app.models.binder import Binder
from app.models.publisher import Publisher
from app.services.bedrock import bedrock_retry, get_bedrock_client, get_model_id
from app.services.portrait_sync import process_org_entity, process_person_entity

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Map entity types to model classes
_MODEL_MAP: dict[str, type[Author | Publisher | Binder]] = {
    "author": Author,
    "publisher": Publisher,
    "binder": Binder,
}

# Fields eligible for enrichment per entity type (only NULL fields are updated)
_ENRICHMENT_FIELDS: dict[str, list[str]] = {
    "author": ["birth_year", "death_year", "era"],
    "publisher": ["founded_year", "description"],
    "binder": ["founded_year", "closed_year", "full_name"],
}

# Era classification for authors based on birth/death years
_ERA_RANGES = [
    (1500, 1660, "Renaissance"),
    (1660, 1800, "Georgian"),
    (1780, 1850, "Romantic"),
    (1837, 1901, "Victorian"),
    (1901, 1914, "Edwardian"),
    (1914, 2100, "Modern"),
]


def _classify_era(birth_year: int | None, death_year: int | None) -> str | None:
    """Classify an author's era based on their active period.

    Uses the midpoint of their life as the reference point. Falls back to
    death_year - 30 or birth_year + 40 if only one date is available.

    Args:
        birth_year: Author's birth year (may be None)
        death_year: Author's death year (may be None)

    Returns:
        Era string or None if insufficient data
    """
    if birth_year and death_year:
        midpoint = (birth_year + death_year) // 2
    elif death_year:
        midpoint = death_year - 30
    elif birth_year:
        midpoint = birth_year + 40
    else:
        return None

    for start, end, era in _ERA_RANGES:
        if start <= midpoint < end:
            return era
    return None


def _build_enrichment_prompt(entity_type: str, entity_name: str) -> str:
    """Build a Bedrock prompt to research entity metadata.

    Args:
        entity_type: "author", "publisher", or "binder"
        entity_name: Name of the entity to research

    Returns:
        Prompt string for Bedrock
    """
    if entity_type == "author":
        return f"""Research the following author in the context of antiquarian books and publishing history.

Author: {entity_name}

Return ONLY a valid JSON object with these fields:
- "birth_year": integer year of birth, or null if unknown
- "death_year": integer year of death, or null if still living or unknown
- "era": one of "Renaissance", "Georgian", "Romantic", "Victorian", "Edwardian", "Modern", or null

Focus on authors relevant to book collecting, publishing, and literary history.
If the author is not a well-known figure, return null for all fields.
Do NOT guess or fabricate dates. Only provide data you are confident about.

Output ONLY the JSON object, no other text."""

    elif entity_type == "publisher":
        return f"""Research the following publisher in the context of antiquarian books and publishing history.

Publisher: {entity_name}

Return ONLY a valid JSON object with these fields:
- "founded_year": integer year the publisher was founded, or null if unknown
- "description": a brief 1-2 sentence description of the publisher's significance in book history, or null

Focus on publishers relevant to book collecting, especially Victorian and fine press publishers.
If the publisher is not a well-known firm, return null for all fields.
Do NOT guess or fabricate dates. Only provide data you are confident about.

Output ONLY the JSON object, no other text."""

    else:  # binder
        return f"""Research the following bookbinder or binding house in the context of antiquarian books.

Binder/Binding House: {entity_name}

Return ONLY a valid JSON object with these fields:
- "founded_year": integer year the bindery was founded or the binder began working, or null if unknown
- "closed_year": integer year the bindery closed or the binder stopped working, or null if still operating or unknown
- "full_name": the full formal name of the binder or binding house if different from the common name, or null

Focus on binders relevant to fine binding, especially Victorian era and art binding.
If the binder is not a well-known figure, return null for all fields.
Do NOT guess or fabricate dates. Only provide data you are confident about.

Output ONLY the JSON object, no other text."""


def _parse_enrichment_response(response_text: str) -> dict[str, Any]:
    """Parse JSON from Bedrock response, handling markdown code blocks.

    Args:
        response_text: Raw text response from Bedrock

    Returns:
        Parsed dict of enrichment data

    Raises:
        json.JSONDecodeError: If response is not valid JSON
    """
    text = response_text.strip()

    # Handle markdown code blocks
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    return json.loads(text.strip())


@bedrock_retry(max_retries=2, base_delay=2.0)
def _call_bedrock_for_enrichment(prompt: str) -> str:
    """Call Bedrock Haiku with the enrichment prompt.

    Uses Haiku for cost-effectiveness (entity lookups are simple tasks).

    Args:
        prompt: The enrichment prompt

    Returns:
        Raw response text from Bedrock
    """
    client = get_bedrock_client()
    model_id = get_model_id("haiku")

    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "temperature": 0.0,
            "messages": [{"role": "user", "content": prompt}],
        }
    )

    response = client.invoke_model(
        modelId=model_id,
        body=body,
        contentType="application/json",
        accept="application/json",
    )

    response_body = json.loads(response["body"].read())
    return response_body["content"][0]["text"]


def _apply_enrichment(
    db: Session,
    entity_type: str,
    entity_id: int,
    enrichment_data: dict[str, Any],
) -> list[str]:
    """Apply enrichment data to entity, only updating NULL fields.

    Args:
        db: Database session
        entity_type: "author", "publisher", or "binder"
        entity_id: Entity primary key
        enrichment_data: Dict of field values from Bedrock

    Returns:
        List of field names that were updated
    """
    model_class = _MODEL_MAP[entity_type]
    entity = db.query(model_class).filter(model_class.id == entity_id).first()

    if not entity:
        logger.warning("Entity %s:%s not found for enrichment", entity_type, entity_id)
        return []

    allowed_fields = _ENRICHMENT_FIELDS[entity_type]
    updated_fields = []

    for field in allowed_fields:
        if field not in enrichment_data:
            continue

        new_value = enrichment_data[field]
        if new_value is None:
            continue

        # Only update NULL fields (never overwrite user-provided data)
        current_value = getattr(entity, field, None)
        if current_value is not None:
            logger.debug(
                "Skipping %s.%s — already has value %r",
                entity_type,
                field,
                current_value,
            )
            continue

        # Validate integer fields
        if field in ("birth_year", "death_year", "founded_year", "closed_year"):
            if not isinstance(new_value, int):
                try:
                    new_value = int(new_value)
                except (ValueError, TypeError):
                    logger.warning(
                        "Invalid %s value for %s:%s: %r",
                        field,
                        entity_type,
                        entity_id,
                        new_value,
                    )
                    continue

            # Sanity check: years should be reasonable for book history
            if not (1400 <= new_value <= 2100):
                logger.warning(
                    "Unreasonable %s value for %s:%s: %d",
                    field,
                    entity_type,
                    entity_id,
                    new_value,
                )
                continue

        # Truncate string fields to model column limits
        if field == "full_name" and isinstance(new_value, str) and len(new_value) > 200:
            new_value = new_value[:200]

        setattr(entity, field, new_value)
        updated_fields.append(field)

    # For authors: derive era from birth/death years if era is still NULL
    if entity_type == "author" and getattr(entity, "era", None) is None:
        derived_era = _classify_era(
            getattr(entity, "birth_year", None),
            getattr(entity, "death_year", None),
        )
        if derived_era:
            entity.era = derived_era
            updated_fields.append("era")

    if updated_fields:
        db.commit()
        logger.info(
            "Enriched %s:%s — updated fields: %s",
            entity_type,
            entity_id,
            ", ".join(updated_fields),
        )
    else:
        logger.info(
            "No enrichment applied for %s:%s — all fields already populated or no data found",
            entity_type,
            entity_id,
        )

    return updated_fields


def _trigger_portrait_sync(db: Session, entity_type: str, entity_id: int) -> None:
    """Trigger portrait sync for a single entity after enrichment.

    Fetches the entity from the DB and calls the appropriate portrait sync
    function (person for authors, org for publishers/binders).

    Portrait sync failures are logged as warnings but never propagated —
    enrichment success must not depend on portrait availability.

    Args:
        db: Database session
        entity_type: "author", "publisher", or "binder"
        entity_id: Entity primary key
    """
    logger.info("Starting portrait sync for %s %s", entity_type, entity_id)

    try:
        model_class = _MODEL_MAP[entity_type]
        entity = db.query(model_class).filter(model_class.id == entity_id).first()

        if not entity:
            logger.warning("Portrait sync skipped — %s %s not found", entity_type, entity_id)
            return

        if entity_type == "author":
            result = process_person_entity(db, entity, entity_type, threshold=0.7, dry_run=False)
        else:
            # publisher and binder use org entity processing
            result = process_org_entity(db, entity, entity_type, threshold=0.7, dry_run=False)

        logger.info(
            "Portrait sync complete for %s %s: %s",
            entity_type,
            entity_id,
            result.get("status"),
        )

    except Exception as e:
        logger.warning("Portrait sync failed for %s %s: %s", entity_type, entity_id, str(e))


def handle_entity_enrichment_message(message: dict, db: Session) -> None:
    """Process a single entity enrichment message.

    Args:
        message: Dict with keys: entity_type, entity_id, entity_name
        db: Database session
    """
    entity_type = message["entity_type"]
    entity_id = message["entity_id"]
    entity_name = message["entity_name"]

    if entity_type not in _MODEL_MAP:
        logger.error("Unknown entity type: %s", entity_type)
        return

    try:
        prompt = _build_enrichment_prompt(entity_type, entity_name)
        response_text = _call_bedrock_for_enrichment(prompt)
        enrichment_data = _parse_enrichment_response(response_text)

        logger.info(
            "Bedrock returned enrichment for %s:%s (%s): %s",
            entity_type,
            entity_id,
            entity_name,
            enrichment_data,
        )

        _apply_enrichment(db, entity_type, entity_id, enrichment_data)

        # After successful enrichment, trigger portrait sync.
        # This is wrapped in its own error handling inside _trigger_portrait_sync
        # so portrait failures never cause enrichment to appear failed.
        _trigger_portrait_sync(db, entity_type, entity_id)

    except ClientError as e:
        logger.error(
            "Bedrock error enriching %s:%s (%s): %s",
            entity_type,
            entity_id,
            entity_name,
            e,
        )
    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse enrichment response for %s:%s (%s): %s",
            entity_type,
            entity_id,
            entity_name,
            e,
        )
    except Exception:
        logger.exception(
            "Unexpected error enriching %s:%s (%s)",
            entity_type,
            entity_id,
            entity_name,
        )


def handler(event: dict, context: object) -> dict:
    """Lambda handler for SQS entity enrichment messages.

    Supports version check via {"version": true} payload.

    Args:
        event: SQS event containing batch of messages, or version check payload
        context: Lambda context

    Returns:
        Dict with batch item failures for partial batch response,
        or version info if version check requested
    """
    # Handle version check (for smoke tests)
    if event.get("version"):
        from app.config import get_settings

        settings = get_settings()
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "version": getattr(settings, "app_version", "unknown"),
                    "worker": "entity-enrichment",
                }
            ),
        }

    batch_item_failures = []

    for record in event.get("Records", []):
        message_id = record.get("messageId", "unknown")

        try:
            body = json.loads(record["body"])
            logger.info(
                "Processing entity enrichment for %s:%s (%s)",
                body.get("entity_type"),
                body.get("entity_id"),
                body.get("entity_name"),
            )

            db = SessionLocal()
            try:
                handle_entity_enrichment_message(body, db)
            finally:
                db.close()

            logger.info("Successfully processed enrichment message %s", message_id)

        except Exception:
            logger.exception("Failed to process enrichment message %s", message_id)
            batch_item_failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": batch_item_failures}
