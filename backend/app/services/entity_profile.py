"""Entity profile service -- assembles profile data from DB."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.config import get_settings
from app.enums import OWNED_STATUSES
from app.models.ai_connection import AIConnection
from app.models.author import Author
from app.models.binder import Binder
from app.models.book import Book
from app.models.entity_profile import EntityProfile
from app.models.image import BookImage
from app.models.publisher import Publisher
from app.schemas.entity_profile import (
    EntityProfileResponse,
    EntityType,
    ProfileBook,
    ProfileConnection,
    ProfileData,
    ProfileEntity,
    ProfileStats,
    RelationshipNarrative,
)
from app.schemas.social_circles import SocialCircleNode, SocialCirclesResponse
from app.services.ai_profile_generator import (
    GeneratorConfig,
    generate_ai_connections,
    generate_bio_and_stories,
    generate_connection_narrative,
    generate_relationship_story,
    strip_invalid_markers,
)
from app.services.narrative_classifier import classify_connection
from app.services.social_circles_cache import get_or_build_graph

logger = logging.getLogger(__name__)


# Map entity type strings to SQLAlchemy model classes.
_MODEL_MAP: dict[str, type[Author | Publisher | Binder]] = {
    "author": Author,
    "publisher": Publisher,
    "binder": Binder,
}

# Map entity type strings to their Book FK columns.
_ENTITY_FK_MAP: dict[str, InstrumentedAttribute] = {
    "author": Book.author_id,
    "publisher": Book.publisher_id,
    "binder": Book.binder_id,
}

assert _MODEL_MAP.keys() == _ENTITY_FK_MAP.keys(), (
    "_MODEL_MAP and _ENTITY_FK_MAP must have identical keys"
)

# Triggers that receive full AI-generated relationship stories.
_HIGH_IMPACT_TRIGGERS = frozenset({"cross_era_bridge", "social_circle"})

# Maximum shared books to include per connection.
_MAX_SHARED_BOOKS_PER_CONNECTION = 5

# Maximum connections to include in AI prompts to control token cost (#1654).
_MAX_PROMPT_CONNECTIONS = 15

# Maximum connections that receive narrative generation to cap Lambda runtime (#1718).
_MAX_NARRATIVE_CONNECTIONS = 8


def _store_ai_connections(db: Session, connections: list[dict]) -> int:
    """Store validated AI connections to canonical table (upsert).

    Uses canonical ordering (lower node ID string first) to prevent
    duplicate A→B / B→A storage.  On conflict, keeps the higher-confidence
    version.  Returns the number of rows written/updated.

    On PostgreSQL, uses a single ``INSERT … ON CONFLICT DO UPDATE`` for the
    entire batch.  On other dialects (SQLite in tests) falls back to
    per-row upsert.
    """
    rows: list[dict] = []
    for conn in connections:
        src_type = conn.get("source_type")
        src_id = conn.get("source_id")
        tgt_type = conn.get("target_type")
        tgt_id = conn.get("target_id")
        relationship = conn.get("relationship")

        if not all(v is not None for v in (src_type, src_id, tgt_type, tgt_id, relationship)):
            continue

        # Canonical ordering — lower node ID string first
        src_key = f"{src_type}:{src_id}"
        tgt_key = f"{tgt_type}:{tgt_id}"
        if src_key > tgt_key:
            src_type, tgt_type = tgt_type, src_type
            src_id, tgt_id = tgt_id, src_id

        confidence = max(0.0, min(float(conn.get("confidence", 0.5)), 1.0))

        rows.append(
            {
                "source_type": src_type,
                "source_id": src_id,
                "target_type": tgt_type,
                "target_id": tgt_id,
                "relationship": relationship,
                "sub_type": conn.get("sub_type"),
                "confidence": confidence,
                "evidence": conn.get("evidence"),
            }
        )

    if not rows:
        return 0

    dialect = db.bind.dialect.name if db.bind else ""
    if dialect == "postgresql":
        count = _batch_upsert_pg(db, rows)
    else:
        count = _upsert_fallback(db, rows)

    if count:
        db.flush()
    return count


def _batch_upsert_pg(db: Session, rows: list[dict]) -> int:
    """PostgreSQL fast path: single INSERT … ON CONFLICT DO UPDATE."""
    from sqlalchemy.dialects.postgresql import insert

    stmt = insert(AIConnection).values(rows)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_ai_connection",
        set_={
            "confidence": func.greatest(
                stmt.excluded.confidence,
                func.coalesce(AIConnection.confidence, 0.0),
            ),
            "evidence": stmt.excluded.evidence,
            "sub_type": stmt.excluded.sub_type,
        },
    )
    result = db.execute(stmt)
    return result.rowcount  # type: ignore[return-value]


def _upsert_fallback(db: Session, rows: list[dict]) -> int:
    """Per-row upsert for non-PostgreSQL dialects (SQLite in tests)."""
    count = 0
    for row in rows:
        existing = (
            db.query(AIConnection)
            .filter(
                AIConnection.source_type == row["source_type"],
                AIConnection.source_id == row["source_id"],
                AIConnection.target_type == row["target_type"],
                AIConnection.target_id == row["target_id"],
                AIConnection.relationship == row["relationship"],
            )
            .first()
        )

        if existing:
            if row["confidence"] > existing.confidence:
                existing.confidence = row["confidence"]
                existing.evidence = row["evidence"]
                existing.sub_type = row["sub_type"]
                count += 1
        else:
            db.add(AIConnection(**row))
            count += 1

    return count


def _get_all_collection_entities(db: Session) -> list[dict]:
    """Fetch all collection entities for AI connection discovery.

    Returns list of dicts with entity_type, entity_id, name for all
    authors, publishers, and binders that have at least one owned book.
    """
    entities: list[dict] = []
    for entity_type_str, model_cls in _MODEL_MAP.items():
        fk_column = _ENTITY_FK_MAP[entity_type_str]
        # Subquery: entity IDs that have at least one owned book
        entity_ids_with_books = (
            db.query(fk_column)
            .filter(Book.status.in_(OWNED_STATUSES), fk_column.isnot(None))
            .distinct()
            .subquery()
        )
        rows = (
            db.query(model_cls.id, model_cls.name)
            .filter(model_cls.id.in_(entity_ids_with_books))
            .all()
        )
        for row in rows:
            entities.append({"entity_type": entity_type_str, "entity_id": row.id, "name": row.name})
    return entities


def _get_entity(
    db: Session, entity_type: str, entity_id: int
) -> Author | Publisher | Binder | None:
    """Fetch entity from appropriate table."""
    model = _MODEL_MAP.get(entity_type)
    if not model:
        return None
    return db.query(model).filter(model.id == entity_id).first()


def _get_entity_books(db: Session, entity_type: str, entity_id: int) -> list[Book]:
    """Fetch owned books for an entity."""
    fk_column = _ENTITY_FK_MAP.get(entity_type)
    if fk_column is None:
        return []
    filters = [Book.status.in_(OWNED_STATUSES), fk_column == entity_id]
    return db.query(Book).filter(*filters).order_by(Book.year_start.asc()).all()


def _build_profile_entity(entity: Author | Publisher | Binder, entity_type: str) -> ProfileEntity:
    """Convert DB entity to ProfileEntity schema."""
    return ProfileEntity(
        id=entity.id,
        type=EntityType(entity_type),
        name=entity.name,
        birth_year=getattr(entity, "birth_year", None),
        death_year=getattr(entity, "death_year", None),
        founded_year=getattr(entity, "founded_year", None),
        closed_year=getattr(entity, "closed_year", None),
        era=getattr(entity, "era", None),
        tier=getattr(entity, "tier", None),
        image_url=getattr(entity, "image_url", None),
    )


def _node_to_profile_entity(node: SocialCircleNode) -> ProfileEntity:
    """Convert a graph node to ProfileEntity schema.

    Unlike _build_profile_entity (which takes a DB model), this takes
    a SocialCircleNode from the cached graph.  Both produce identical
    ProfileEntity objects including image_url (#1840).
    """
    type_str = node.type.value if hasattr(node.type, "value") else str(node.type)
    return ProfileEntity(
        id=node.entity_id,
        type=EntityType(type_str),
        name=node.name,
        birth_year=node.birth_year,
        death_year=node.death_year,
        founded_year=node.founded_year,
        closed_year=node.closed_year,
        era=_era_str(node),
        tier=node.tier,
        image_url=node.image_url if isinstance(node.image_url, str) else None,
    )


def _get_primary_image_map(db: Session, book_ids: list[int]) -> dict[int, BookImage]:
    """Batch-load primary images for books, returning {book_id: BookImage}.

    Picks the is_primary=True image for each book, or falls back to the
    image with the lowest display_order.
    """
    if not book_ids:
        return {}

    images = (
        db.query(BookImage)
        .filter(BookImage.book_id.in_(book_ids))
        .order_by(BookImage.display_order)
        .all()
    )

    image_map: dict[int, BookImage] = {}
    for img in images:
        if img.book_id not in image_map or img.is_primary:
            image_map[img.book_id] = img

    return image_map


def _image_url(book_id: int, image: BookImage, *, is_lambda: bool) -> str:
    """Build image URL for a BookImage, using CloudFront in Lambda or relative URL locally."""
    if is_lambda:
        from app.utils.cdn import get_cloudfront_url

        return get_cloudfront_url(image.s3_key)
    return f"/api/v1/books/{book_id}/images/{image.id}/file"


def _build_profile_books(db: Session, books: list[Book]) -> list[ProfileBook]:
    """Convert Book models to ProfileBook schemas with primary image URLs."""
    image_map = _get_primary_image_map(db, [b.id for b in books])
    is_lambda = get_settings().is_aws_lambda

    result: list[ProfileBook] = []
    for book in books:
        img = image_map.get(book.id)
        result.append(
            ProfileBook(
                id=book.id,
                title=book.title,
                year=book.year_start,
                condition=book.condition_grade,
                edition=book.edition,
                primary_image_url=_image_url(book.id, img, is_lambda=is_lambda) if img else None,
            )
        )
    return result


def _build_stats(books: list[Book]) -> ProfileStats:
    """Calculate collection stats from books."""
    if not books:
        return ProfileStats()

    years = [b.year_start for b in books if b.year_start]
    values = [float(b.value_mid) for b in books if b.value_mid is not None]

    # Condition distribution: count books per condition grade
    condition_distribution: dict[str, int] = {}
    for b in books:
        grade = b.condition_grade if b.condition_grade else "UNGRADED"
        condition_distribution[grade] = condition_distribution.get(grade, 0) + 1

    # Acquisition by year: count books per purchase year, sorted ascending
    acquisition_by_year: dict[int, int] = {}
    for b in books:
        if b.purchase_date:
            yr = b.purchase_date.year
            acquisition_by_year[yr] = acquisition_by_year.get(yr, 0) + 1
    acquisition_by_year = dict(sorted(acquisition_by_year.items()))

    return ProfileStats(
        total_books=len(books),
        total_estimated_value=sum(values) if values else None,
        first_editions=sum(1 for b in books if b.is_first_edition),
        date_range=[min(years), max(years)] if years else [],
        condition_distribution=condition_distribution,
        acquisition_by_year=acquisition_by_year,
    )


def is_profile_stale(
    db: Session,
    entity_type: str,
    entity_id: int,
    *,
    profile: EntityProfile | None = None,
) -> bool:
    """Check if entity needs profile (re)generation.

    Returns True if:
      - No profile exists for this entity
      - Profile exists but books have been updated since generation

    Pass an already-fetched *profile* to avoid a duplicate query.
    """
    if profile is None:
        profile = (
            db.query(EntityProfile)
            .filter(
                EntityProfile.entity_type == entity_type,
                EntityProfile.entity_id == entity_id,
            )
            .first()
        )
    if not profile or not profile.generated_at:
        return True

    fk_column = _ENTITY_FK_MAP.get(entity_type)
    if fk_column is None:
        return False

    latest_update = (
        db.query(func.max(Book.updated_at))
        .filter(Book.status.in_(OWNED_STATUSES), fk_column == entity_id)
        .scalar()
    )
    return bool(latest_update and latest_update > profile.generated_at)


def _era_str(node) -> str | None:
    """Extract era as a plain string from a social circles node."""
    if node.era is None:
        return None
    return node.era.value if hasattr(node.era, "value") else str(node.era)


def _node_years(node) -> tuple[int | None, int | None]:
    """Extract (start_year, end_year) from a social circles node."""
    return (
        node.birth_year or node.founded_year,
        node.death_year or node.closed_year,
    )


def _iter_connected_entities(
    node_id: str,
    graph: SocialCirclesResponse,
) -> Iterator[tuple[str, int, str, Any, Any]]:
    """Yield (entity_type, entity_id, name, node, edge) for each connected entity.

    Edges are sorted by strength descending so highest-strength connections
    come first.  Edges whose "other" node cannot be resolved are skipped.
    """
    connected_edges = sorted(
        (e for e in graph.edges if e.source == node_id or e.target == node_id),
        key=lambda e: e.strength,
        reverse=True,
    )
    node_map = {n.id: n for n in graph.nodes}
    for edge in connected_edges:
        other_id = edge.target if edge.source == node_id else edge.source
        node = node_map.get(other_id)
        if not node:
            continue
        type_str = node.type.value if hasattr(node.type, "value") else str(node.type)
        yield type_str, node.entity_id, node.name, node, edge


def _format_entity_dates(node) -> str:
    """Format entity dates as a human-readable string for AI prompts."""
    if node.birth_year:
        death = node.death_year or "?"
        return f"{node.birth_year}-{death}"
    if node.founded_year:
        closed = node.closed_year or "present"
        return f"est. {node.founded_year}-{closed}"
    return "dates unknown"


def _build_connections(
    db: Session,
    entity_type: str,
    entity_id: int,
    profile: EntityProfile | None,
    graph: SocialCirclesResponse | None = None,
) -> list[ProfileConnection]:
    """Build connection list from social circles graph.

    Enriches each connection with:
    - narrative_trigger from classify_connection (#1553)
    - shared_books as ProfileBook objects (#1556)
    - cached relationship_story from profile (#1553)
    """
    node_id = f"{entity_type}:{entity_id}"
    if graph is None:
        graph = get_or_build_graph(db)

    # Resolve source node and count edges (needed before iterating)
    source_node = next((n for n in graph.nodes if n.id == node_id), None)
    source_connection_count = sum(
        1 for e in graph.edges if e.source == node_id or e.target == node_id
    )

    # Materialise connected entities so we can bulk-fetch shared books
    connected = list(_iter_connected_entities(node_id, graph))

    # Bulk-fetch shared books for all edges in a single query
    all_shared_ids: set[int] = set()
    for _etype, _eid, _name, _node, edge in connected:
        if edge.shared_book_ids:
            all_shared_ids.update(edge.shared_book_ids)

    shared_book_lookup: dict[int, Book] = {}
    if all_shared_ids:
        shared_books_db = db.query(Book).filter(Book.id.in_(all_shared_ids)).all()
        shared_book_lookup = {b.id: b for b in shared_books_db}

    # Batch-load primary images for shared books (#1634)
    shared_image_map = _get_primary_image_map(db, list(all_shared_ids))
    is_lambda = get_settings().is_aws_lambda

    # Get cached narratives and relationship stories
    narratives: dict[str, str] = {}
    rel_stories: dict[str, dict] = {}
    if profile and profile.connection_narratives:
        narratives = profile.connection_narratives
    if profile and profile.relationship_stories:
        rel_stories = profile.relationship_stories

    connections: list[ProfileConnection] = []
    for _type_str, _eid, _name, other_node, edge in connected:
        other_id = edge.target if edge.source == node_id else edge.source
        narrative_key = f"{node_id}:{other_id}"
        narrative_key_rev = f"{other_id}:{node_id}"

        era_value = _era_str(other_node)
        conn_type_str = edge.type.value if hasattr(edge.type, "value") else str(edge.type)

        # Classify connection (#1553)
        cached_story_data = rel_stories.get(narrative_key) or rel_stories.get(narrative_key_rev)
        narrative_trigger = classify_connection(
            source_era=_era_str(source_node) if source_node else None,
            target_era=era_value,
            source_years=_node_years(source_node) if source_node else (None, None),
            target_years=_node_years(other_node),
            connection_type=conn_type_str,
            source_connection_count=source_connection_count,
            has_relationship_story=bool(cached_story_data),
        )

        # Build shared books capped at _MAX_SHARED_BOOKS_PER_CONNECTION (#1556)
        shared_books: list[ProfileBook] = []
        if edge.shared_book_ids:
            for book_id in edge.shared_book_ids[:_MAX_SHARED_BOOKS_PER_CONNECTION]:
                book = shared_book_lookup.get(book_id)
                if book:
                    img = shared_image_map.get(book.id)
                    shared_books.append(
                        ProfileBook(
                            id=book.id,
                            title=book.title,
                            year=book.year_start,
                            condition=book.condition_grade,
                            edition=book.edition,
                            primary_image_url=(
                                _image_url(book.id, img, is_lambda=is_lambda) if img else None
                            ),
                        )
                    )

        # Reconstruct cached relationship story
        relationship_story = None
        if cached_story_data and isinstance(cached_story_data, dict):
            try:
                relationship_story = RelationshipNarrative(**cached_story_data)
            except Exception:
                logger.warning(
                    "Invalid cached relationship story for %s", narrative_key, exc_info=True
                )

        connections.append(
            ProfileConnection(
                entity=_node_to_profile_entity(other_node),
                connection_type=conn_type_str,
                strength=edge.strength,
                shared_book_count=len(edge.shared_book_ids) if edge.shared_book_ids else 0,
                shared_books=shared_books,
                narrative=narratives.get(narrative_key) or narratives.get(narrative_key_rev),
                narrative_trigger=narrative_trigger,
                is_key=False,
                relationship_story=relationship_story,
            )
        )

    # Merge AI-discovered connections from canonical table (#1813)
    ai_rows = (
        db.query(AIConnection)
        .filter(
            or_(
                (AIConnection.source_type == entity_type) & (AIConnection.source_id == entity_id),
                (AIConnection.target_type == entity_type) & (AIConnection.target_id == entity_id),
            )
        )
        .all()
    )
    if ai_rows:
        # Build set of existing (target, relationship) pairs to avoid duplicates
        existing_edges = {
            (
                f"{c.entity.type.value if hasattr(c.entity.type, 'value') else c.entity.type}:{c.entity.id}",
                c.connection_type,
            )
            for c in connections
        }
        for row in ai_rows:
            # Determine which end is the "other" entity
            if row.source_type == entity_type and row.source_id == entity_id:
                other_type, other_id = row.target_type, row.target_id
            else:
                other_type, other_id = row.source_type, row.source_id

            target_key = f"{other_type}:{other_id}"
            strength = max(2, min(int(row.confidence * 10), 10))
            edge_key = (target_key, row.relationship)

            # Skip if same target+relationship already exists
            if edge_key in existing_edges:
                # Enrich existing connection with AI fields (same relationship type)
                for conn in connections:
                    et = (
                        conn.entity.type.value
                        if hasattr(conn.entity.type, "value")
                        else conn.entity.type
                    )
                    if (
                        et == other_type
                        and conn.entity.id == other_id
                        and conn.connection_type == row.relationship
                    ):
                        conn.is_ai_discovered = True
                        conn.sub_type = row.sub_type
                        conn.confidence = row.confidence
                        break
                continue

            # Look up target entity — prefer graph nodes (richer metadata),
            # fall back to DB so AI connections aren't silently dropped when
            # the target is missing from the cached graph (#1827).
            target_node_id = f"{other_type}:{other_id}"
            target_node = (
                next((n for n in graph.nodes if n.id == target_node_id), None)
                if graph is not None
                else None
            )

            if target_node:
                entity_data = _node_to_profile_entity(target_node)
            else:
                # Graph miss — resolve from DB so the connection still appears
                db_entity = _get_entity(db, other_type, other_id)
                if not db_entity:
                    continue
                entity_data = _build_profile_entity(db_entity, other_type)

            connections.append(
                ProfileConnection(
                    entity=entity_data,
                    connection_type=row.relationship,
                    strength=strength,
                    shared_book_count=0,
                    narrative=row.evidence,
                    is_key=False,
                    is_ai_discovered=True,
                    sub_type=row.sub_type,
                    confidence=row.confidence,
                )
            )
            existing_edges.add(edge_key)

    # Sort by strength with mild AI boost (1.2x) — strong book connections
    # still rank above weak AI guesses, but equal-strength AI connections win
    connections.sort(
        key=lambda c: c.strength * (1.2 if c.is_ai_discovered else 1.0),
        reverse=True,
    )

    # Mark top 5 as key connections
    # Personal (AI-discovered) connections get priority for key slots
    seen_types: set[str] = set()
    key_count = 0
    # First pass: AI-discovered connections get first key slots
    for conn in connections:
        if key_count >= 3:
            break
        if conn.is_ai_discovered and conn.connection_type not in seen_types:
            conn.is_key = True
            seen_types.add(conn.connection_type)
            key_count += 1
    # Second pass: diverse types from remaining connections
    for conn in connections:
        if key_count >= 3:
            break
        if not conn.is_key and conn.connection_type not in seen_types:
            conn.is_key = True
            seen_types.add(conn.connection_type)
            key_count += 1
    # Third pass: fill remaining slots (up to 5) by strength regardless of type
    for conn in connections:
        if key_count >= 5:
            break
        if not conn.is_key:
            conn.is_key = True
            key_count += 1

    return connections


def get_entity_profile(
    db: Session,
    entity_type: str,
    entity_id: int,
) -> EntityProfileResponse | None:
    """Assemble full entity profile response."""
    entity = _get_entity(db, entity_type, entity_id)
    if not entity:
        return None

    books = _get_entity_books(db, entity_type, entity_id)

    # Fetch cached profile — profiles are per-entity, not per-user (#1715).
    cached = (
        db.query(EntityProfile)
        .filter(
            EntityProfile.entity_type == entity_type,
            EntityProfile.entity_id == entity_id,
        )
        .first()
    )

    is_stale = is_profile_stale(db, entity_type, entity_id, profile=cached)

    profile_data = ProfileData(
        bio_summary=cached.bio_summary if cached else None,
        personal_stories=cached.personal_stories if cached and cached.personal_stories else [],
        is_stale=is_stale,
        generated_at=cached.generated_at if cached else None,
        model_version=cached.model_version if cached else None,
    )

    graph = get_or_build_graph(db)
    connections = _build_connections(db, entity_type, entity_id, cached, graph=graph)

    return EntityProfileResponse(
        entity=_build_profile_entity(entity, entity_type),
        profile=profile_data,
        connections=connections,
        books=_build_profile_books(db, books),
        stats=_build_stats(books),
    )


def generate_and_cache_profile(
    db: Session,
    entity_type: str,
    entity_id: int,
    max_narratives: int | None = None,
    graph: SocialCirclesResponse | None = None,
    all_entities: list[dict] | None = None,
) -> EntityProfile:
    """Generate AI profile and cache in DB."""
    t_total = time.monotonic()

    entity = _get_entity(db, entity_type, entity_id)
    if not entity:
        raise ValueError(f"Entity {entity_type}:{entity_id} not found")

    books = _get_entity_books(db, entity_type, entity_id)
    book_titles = [b.title for b in books]

    # Resolve config ONCE for all AI calls in this profile generation
    config = GeneratorConfig.resolve(db)

    # Resolve narrative cap: explicit param overrides the constant (#1718)
    effective_max_narratives = (
        max_narratives if max_narratives is not None else _MAX_NARRATIVE_CONNECTIONS
    )

    # Build graph and connection list for cross-link markers (#1618)
    node_id = f"{entity_type}:{entity_id}"
    t0 = time.monotonic()
    if graph is None:
        graph = get_or_build_graph(db)

    # Resolve source node and count edges (needed before iterating)
    source_node = next((n for n in graph.nodes if n.id == node_id), None)
    source_connection_count = sum(
        1 for e in graph.edges if e.source == node_id or e.target == node_id
    )

    # Materialise connected entities (sorted by strength descending)
    connected = list(_iter_connected_entities(node_id, graph))

    connection_list = [
        {"entity_type": etype, "entity_id": eid, "name": name}
        for etype, eid, name, _node, _edge in connected
    ]
    valid_entity_ids = {f"{c['entity_type']}:{c['entity_id']}" for c in connection_list}

    # Cap connections in AI prompts to control token cost (#1654)
    prompt_connections = connection_list[:_MAX_PROMPT_CONNECTIONS]
    logger.info(
        "profile[%s:%d] graph+connections built in %.1fs (%d connections)",
        entity_type,
        entity_id,
        time.monotonic() - t0,
        len(connected),
    )

    # Discover AI connections BEFORE bio generation so bios can reference them (#1803)
    t0 = time.monotonic()
    if all_entities is None:
        all_entities = _get_all_collection_entities(db)
    ai_connections = generate_ai_connections(
        entity_name=entity.name,
        entity_type=entity_type,
        entity_id=entity_id,
        all_entities=all_entities,
        config=config,
    )
    # Persist AI connections to canonical table (#1813)
    if ai_connections:
        stored = _store_ai_connections(db, ai_connections)
        logger.info(
            "profile[%s:%d] stored %d AI connections to table",
            entity_type,
            entity_id,
            stored,
        )
    logger.info(
        "profile[%s:%d] AI connection discovery took %.1fs",
        entity_type,
        entity_id,
        time.monotonic() - t0,
    )

    # Generate bio + personal stories
    t0 = time.monotonic()
    bio_data = generate_bio_and_stories(
        name=entity.name,
        entity_type=entity_type,
        birth_year=getattr(entity, "birth_year", None),
        death_year=getattr(entity, "death_year", None),
        founded_year=getattr(entity, "founded_year", None),
        book_titles=book_titles,
        connections=prompt_connections,
        config=config,
    )

    logger.info(
        "profile[%s:%d] bio+stories generation took %.1fs",
        entity_type,
        entity_id,
        time.monotonic() - t0,
    )

    if not bio_data.get("biography"):
        logger.warning(
            "AI generation returned empty biography for %s:%d",
            entity_type,
            entity_id,
        )

    # Validate cross-link markers in bio and stories
    if bio_data.get("biography"):
        bio_data["biography"] = strip_invalid_markers(bio_data["biography"], valid_entity_ids)
    for story in bio_data.get("personal_stories", []):
        if story.get("text"):
            story["text"] = strip_invalid_markers(story["text"], valid_entity_ids)

    # Generate connection narratives using trigger-based selection (#1553)
    t0 = time.monotonic()
    narratives: dict[str, str] = {}
    rel_stories: dict[str, dict] = {}
    narrated_count = 0
    for other_type_str, _eid, _name, other_node, edge in connected:
        if narrated_count >= effective_max_narratives:
            break

        other_id = edge.target if edge.source == node_id else edge.source
        conn_type_str = edge.type.value if hasattr(edge.type, "value") else str(edge.type)
        shared_ids_set = set(edge.shared_book_ids) if edge.shared_book_ids else set()
        shared_titles = [b.title for b in books if b.id in shared_ids_set]
        key = f"{node_id}:{other_id}"

        # Classify to decide what AI content to generate
        trigger = classify_connection(
            source_era=_era_str(source_node) if source_node else None,
            target_era=_era_str(other_node),
            source_years=_node_years(source_node) if source_node else (None, None),
            target_years=_node_years(other_node),
            connection_type=conn_type_str,
            source_connection_count=source_connection_count,
            has_relationship_story=False,
        )

        if not trigger:
            continue

        if trigger in _HIGH_IMPACT_TRIGGERS:
            # Generate full relationship story for high-impact connections
            story = generate_relationship_story(
                entity1_name=entity.name,
                entity1_type=entity_type,
                entity1_dates=_format_entity_dates(source_node) if source_node else "dates unknown",
                entity2_name=other_node.name,
                entity2_type=other_type_str,
                entity2_dates=_format_entity_dates(other_node),
                connection_type=conn_type_str,
                shared_book_titles=shared_titles,
                trigger_type=trigger,
                connections=prompt_connections,
                config=config,
            )
            if story:
                # Validate markers in story text
                if story.get("summary"):
                    story["summary"] = strip_invalid_markers(story["summary"], valid_entity_ids)
                for detail in story.get("details", []):
                    if detail.get("text"):
                        detail["text"] = strip_invalid_markers(detail["text"], valid_entity_ids)
                rel_stories[key] = story
                # Use story summary as the simple narrative too
                narratives[key] = story.get("summary", "")
                narrated_count += 1
        else:
            # Generate simple narrative for other triggered connections
            narrative = generate_connection_narrative(
                entity1_name=entity.name,
                entity1_type=entity_type,
                entity2_name=other_node.name,
                entity2_type=other_type_str,
                connection_type=conn_type_str,
                shared_book_titles=shared_titles,
                connections=prompt_connections,
                config=config,
            )
            if narrative:
                narratives[key] = strip_invalid_markers(narrative, valid_entity_ids)
                narrated_count += 1

    logger.info(
        "profile[%s:%d] narrative generation took %.1fs (%d narratives)",
        entity_type,
        entity_id,
        time.monotonic() - t0,
        narrated_count,
    )

    model_version = config.model_id

    # Upsert profile — unique constraint on (entity_type, entity_id).
    existing = (
        db.query(EntityProfile)
        .filter(
            EntityProfile.entity_type == entity_type,
            EntityProfile.entity_id == entity_id,
        )
        .first()
    )

    if existing:
        existing.bio_summary = bio_data.get("biography")
        existing.personal_stories = bio_data.get("personal_stories", [])
        existing.connection_narratives = narratives
        # Merge new stories into existing ones to preserve externally-populated
        # stories (e.g. social_circle) that the classifier cannot regenerate.
        merged_stories = dict(existing.relationship_stories or {})
        merged_stories.update(rel_stories)
        existing.relationship_stories = merged_stories
        existing.ai_connections = ai_connections or None
        existing.generated_at = datetime.now(UTC)
        existing.model_version = model_version
        profile = existing
    else:
        profile = EntityProfile(
            entity_type=entity_type,
            entity_id=entity_id,
            bio_summary=bio_data.get("biography"),
            personal_stories=bio_data.get("personal_stories", []),
            connection_narratives=narratives,
            relationship_stories=rel_stories,
            ai_connections=ai_connections or None,
            model_version=model_version,
        )
        db.add(profile)

    t0 = time.monotonic()
    db.commit()
    logger.info(
        "profile[%s:%d] DB upsert+commit took %.1fs",
        entity_type,
        entity_id,
        time.monotonic() - t0,
    )
    logger.info(
        "profile[%s:%d] total generation took %.1fs",
        entity_type,
        entity_id,
        time.monotonic() - t_total,
    )
    return profile
