"""Entity profile service -- assembles profile data from DB."""

from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import func

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
)
from app.services.ai_profile_generator import (
    generate_bio_and_stories,
    generate_connection_narrative,
)
from app.services.social_circles import build_social_circles_graph

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


# Map entity type strings to SQLAlchemy model classes.
_MODEL_MAP: dict[str, type[Author | Publisher | Binder]] = {
    "author": Author,
    "publisher": Publisher,
    "binder": Binder,
}


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
    filters = [Book.status.in_(OWNED_STATUSES)]
    if entity_type == "author":
        filters.append(Book.author_id == entity_id)
    elif entity_type == "publisher":
        filters.append(Book.publisher_id == entity_id)
    elif entity_type == "binder":
        filters.append(Book.binder_id == entity_id)
    else:
        return []
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

    filters = [Book.status.in_(OWNED_STATUSES)]
    if entity_type == "author":
        filters.append(Book.author_id == entity_id)
    elif entity_type == "publisher":
        filters.append(Book.publisher_id == entity_id)
    elif entity_type == "binder":
        filters.append(Book.binder_id == entity_id)
    else:
        return False

    latest_update = db.query(func.max(Book.updated_at)).filter(*filters).scalar()
    if latest_update and latest_update > profile.generated_at:
        return True
    return False


def _build_connections(
    db: Session,
    entity_type: str,
    entity_id: int,
    profile: EntityProfile | None,
) -> list[ProfileConnection]:
    """Build connection list from social circles graph."""
    node_id = f"{entity_type}:{entity_id}"
    graph = build_social_circles_graph(db)

    # Find edges connected to this entity
    connected_edges = [e for e in graph.edges if e.source == node_id or e.target == node_id]

    # Build node lookup
    node_map = {n.id: n for n in graph.nodes}

    # Get cached narratives
    narratives: dict[str, str] = {}
    if profile and profile.connection_narratives:
        narratives = profile.connection_narratives

    connections: list[ProfileConnection] = []
    for edge in connected_edges:
        other_id = edge.target if edge.source == node_id else edge.source
        other_node = node_map.get(other_id)
        if not other_node:
            continue

        narrative_key = f"{node_id}:{other_id}"
        narrative_key_rev = f"{other_id}:{node_id}"

        # Convert Era enum to string value if present
        era_value = None
        if other_node.era is not None:
            era_value = (
                other_node.era.value if hasattr(other_node.era, "value") else str(other_node.era)
            )

        # Convert NodeType enum to EntityType string
        type_str = (
            other_node.type.value if hasattr(other_node.type, "value") else str(other_node.type)
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
                connection_type=edge.type.value if hasattr(edge.type, "value") else str(edge.type),
                strength=edge.strength,
                shared_book_count=len(edge.shared_book_ids) if edge.shared_book_ids else 0,
                shared_books=[],
                narrative=narratives.get(narrative_key) or narratives.get(narrative_key_rev),
                is_key=False,
            )
        )

    # Sort by strength descending
    connections.sort(key=lambda c: c.strength, reverse=True)

    # Mark top 5 as key connections (with type diversity)
    seen_types: set[str] = set()
    key_count = 0
    for conn in connections:
        if key_count >= 5:
            break
        if conn.connection_type not in seen_types or key_count < 3:
            conn.is_key = True
            seen_types.add(conn.connection_type)
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

    connections = _build_connections(db, entity_type, entity_id, cached)

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

    # Generate connection narratives
    node_id = f"{entity_type}:{entity_id}"
    graph = build_social_circles_graph(db)
    connected_edges = [e for e in graph.edges if e.source == node_id or e.target == node_id]
    node_map = {n.id: n for n in graph.nodes}

    narratives: dict[str, str] = {}
    for edge in connected_edges:
        other_id = edge.target if edge.source == node_id else edge.source
        other_node = node_map.get(other_id)
        if not other_node:
            continue

        narrative = generate_connection_narrative(
            entity1_name=entity.name,
            entity1_type=entity_type,
            entity2_name=other_node.name,
            entity2_type=other_node.type.value
            if hasattr(other_node.type, "value")
            else other_node.type,
            connection_type=edge.type.value if hasattr(edge.type, "value") else edge.type,
            shared_book_titles=[b.title for b in books if b.id in (edge.shared_book_ids or [])],
        )
        if narrative:
            narratives[f"{node_id}:{other_id}"] = narrative

    model_version = os.environ.get("ENTITY_PROFILE_MODEL", "claude-3-5-haiku-20241022")

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
        existing.generated_at = datetime.utcnow()
        existing.model_version = model_version
        profile = existing
    else:
        profile = EntityProfile(
            entity_type=entity_type,
            entity_id=entity_id,
            bio_summary=bio_data.get("biography"),
            personal_stories=bio_data.get("personal_stories", []),
            connection_narratives=narratives,
            model_version=model_version,
            owner_id=owner_id,
        )
        db.add(profile)

    db.commit()
    return profile
