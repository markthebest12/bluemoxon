"""Entity profile service -- assembles profile data from DB."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import func
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.enums import OWNED_STATUSES
from app.models.author import Author
from app.models.binder import Binder
from app.models.book import Book
from app.models.entity_profile import EntityProfile
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
from app.schemas.social_circles import SocialCirclesResponse
from app.services.ai_profile_generator import (
    _get_model_id,
    generate_bio_and_stories,
    generate_connection_narrative,
    generate_relationship_story,
)
from app.services.narrative_classifier import classify_connection
from app.services.social_circles_cache import get_or_build_graph

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


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
    )


def _build_profile_books(books: list[Book]) -> list[ProfileBook]:
    """Convert Book models to ProfileBook schemas."""
    return [
        ProfileBook(
            id=book.id,
            title=book.title,
            year=book.year_start,
            condition=book.condition_grade,
            edition=book.edition,
        )
        for book in books
    ]


def _build_stats(books: list[Book]) -> ProfileStats:
    """Calculate collection stats from books."""
    if not books:
        return ProfileStats()

    years = [b.year_start for b in books if b.year_start]
    values = [float(b.value_mid) for b in books if b.value_mid is not None]

    return ProfileStats(
        total_books=len(books),
        total_estimated_value=sum(values) if values else None,
        first_editions=sum(1 for b in books if b.is_first_edition),
        date_range=[min(years), max(years)] if years else [],
    )


def _check_staleness(
    db: Session,
    profile: EntityProfile | None,
    entity_type: str,
    entity_id: int,
) -> bool:
    """Check if profile is stale by comparing against book updates."""
    if not profile or not profile.generated_at:
        return False

    fk_column = _ENTITY_FK_MAP.get(entity_type)
    if fk_column is None:
        return False

    filters = [Book.status.in_(OWNED_STATUSES), fk_column == entity_id]
    latest_update = db.query(func.max(Book.updated_at)).filter(*filters).scalar()
    if latest_update and latest_update > profile.generated_at:
        return True
    return False


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

    # Find edges connected to this entity
    connected_edges = [e for e in graph.edges if e.source == node_id or e.target == node_id]

    # Build node lookup
    node_map = {n.id: n for n in graph.nodes}
    source_node = node_map.get(node_id)
    source_connection_count = len(connected_edges)

    # Bulk-fetch shared books for all edges in a single query
    all_shared_ids: set[int] = set()
    for edge in connected_edges:
        if edge.shared_book_ids:
            all_shared_ids.update(edge.shared_book_ids)

    shared_book_lookup: dict[int, Book] = {}
    if all_shared_ids:
        shared_books_db = db.query(Book).filter(Book.id.in_(all_shared_ids)).all()
        shared_book_lookup = {b.id: b for b in shared_books_db}

    # Get cached narratives and relationship stories
    narratives: dict[str, str] = {}
    rel_stories: dict[str, dict] = {}
    if profile and profile.connection_narratives:
        narratives = profile.connection_narratives
    if profile and profile.relationship_stories:
        rel_stories = profile.relationship_stories

    connections: list[ProfileConnection] = []
    for edge in connected_edges:
        other_id = edge.target if edge.source == node_id else edge.source
        other_node = node_map.get(other_id)
        if not other_node:
            continue

        narrative_key = f"{node_id}:{other_id}"
        narrative_key_rev = f"{other_id}:{node_id}"

        era_value = _era_str(other_node)
        conn_type_str = edge.type.value if hasattr(edge.type, "value") else str(edge.type)
        type_str = (
            other_node.type.value if hasattr(other_node.type, "value") else str(other_node.type)
        )

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
                    shared_books.append(
                        ProfileBook(
                            id=book.id,
                            title=book.title,
                            year=book.year_start,
                            condition=book.condition_grade,
                            edition=book.edition,
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
                entity=ProfileEntity(
                    id=other_node.entity_id,
                    type=EntityType(type_str),
                    name=other_node.name,
                    birth_year=other_node.birth_year,
                    death_year=other_node.death_year,
                    founded_year=other_node.founded_year,
                    closed_year=other_node.closed_year,
                    era=era_value,
                    tier=other_node.tier,
                ),
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

    # Sort by strength descending
    connections.sort(key=lambda c: c.strength, reverse=True)

    # Mark top 5 as key connections (prefer type diversity, then fill by strength)
    seen_types: set[str] = set()
    key_count = 0
    # First pass: prefer diverse types for first 3 slots
    for conn in connections:
        if key_count >= 3:
            break
        if conn.connection_type not in seen_types:
            conn.is_key = True
            seen_types.add(conn.connection_type)
            key_count += 1
    # Second pass: fill remaining slots (up to 5) by strength regardless of type
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
    owner_id: int,
) -> EntityProfileResponse | None:
    """Assemble full entity profile response."""
    entity = _get_entity(db, entity_type, entity_id)
    if not entity:
        return None

    books = _get_entity_books(db, entity_type, entity_id)

    # Fetch cached profile
    cached = (
        db.query(EntityProfile)
        .filter(
            EntityProfile.entity_type == entity_type,
            EntityProfile.entity_id == entity_id,
            EntityProfile.owner_id == owner_id,
        )
        .first()
    )

    is_stale = _check_staleness(db, cached, entity_type, entity_id)

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
        books=_build_profile_books(books),
        stats=_build_stats(books),
    )


def generate_and_cache_profile(
    db: Session,
    entity_type: str,
    entity_id: int,
    owner_id: int,
    max_narratives: int | None = None,
    graph: SocialCirclesResponse | None = None,
) -> EntityProfile:
    """Generate AI profile and cache in DB."""
    entity = _get_entity(db, entity_type, entity_id)
    if not entity:
        raise ValueError(f"Entity {entity_type}:{entity_id} not found")

    books = _get_entity_books(db, entity_type, entity_id)
    book_titles = [b.title for b in books]

    # Generate bio + personal stories
    bio_data = generate_bio_and_stories(
        name=entity.name,
        entity_type=entity_type,
        birth_year=getattr(entity, "birth_year", None),
        death_year=getattr(entity, "death_year", None),
        founded_year=getattr(entity, "founded_year", None),
        book_titles=book_titles,
    )

    # Generate connection narratives using trigger-based selection (#1553)
    node_id = f"{entity_type}:{entity_id}"
    if graph is None:
        graph = get_or_build_graph(db)
    connected_edges = [e for e in graph.edges if e.source == node_id or e.target == node_id]
    node_map = {n.id: n for n in graph.nodes}
    source_node = node_map.get(node_id)
    source_connection_count = len(connected_edges)

    narratives: dict[str, str] = {}
    rel_stories: dict[str, dict] = {}
    narrated_count = 0
    for edge in connected_edges:
        if max_narratives and narrated_count >= max_narratives:
            break

        other_id = edge.target if edge.source == node_id else edge.source
        other_node = node_map.get(other_id)
        if not other_node:
            continue

        conn_type_str = edge.type.value if hasattr(edge.type, "value") else str(edge.type)
        other_type_str = (
            other_node.type.value if hasattr(other_node.type, "value") else str(other_node.type)
        )
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
            )
            if story:
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
            )
            if narrative:
                narratives[key] = narrative
                narrated_count += 1

    model_version = _get_model_id()

    # Upsert profile
    existing = (
        db.query(EntityProfile)
        .filter(
            EntityProfile.entity_type == entity_type,
            EntityProfile.entity_id == entity_id,
            EntityProfile.owner_id == owner_id,
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
            model_version=model_version,
            owner_id=owner_id,
        )
        db.add(profile)

    db.commit()
    return profile
