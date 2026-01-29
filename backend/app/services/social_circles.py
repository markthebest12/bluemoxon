# backend/app/services/social_circles.py

"""Social Circles business logic.

Infers connections between authors, publishers, and binders from the books table.
No manual data entry required - all relationships are derived from existing data.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.enums import OWNED_STATUSES
from app.schemas.social_circles import (
    ConnectionType,
    Era,
    NodeType,
    SocialCircleEdge,
    SocialCircleNode,
    SocialCirclesMeta,
    SocialCirclesResponse,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def get_era_from_year(year: int | None) -> Era:
    """Determine historical era from a year."""
    if year is None:
        return Era.unknown
    if year < 1789:
        return Era.pre_romantic
    if year < 1837:
        return Era.romantic
    if year < 1901:
        return Era.victorian
    if year < 1910:
        return Era.edwardian
    return Era.post_1910


def build_social_circles_graph(
    db: Session,
    include_binders: bool = True,
    min_book_count: int = 1,
    era_filter: list[Era] | None = None,
) -> SocialCirclesResponse:
    """Build the social circles graph from book data.

    Args:
        db: Database session
        include_binders: Whether to include binder nodes/edges
        min_book_count: Minimum books for an entity to be included
        era_filter: Optional list of eras to filter by

    Returns:
        SocialCirclesResponse with nodes, edges, and metadata.
    """
    from app.models import Author, Binder, Book, Publisher

    # Fetch owned books (IN_TRANSIT, ON_HAND) - excludes REMOVED, EVALUATING
    # Limit to 5000 to prevent OOM in Lambda (1GB memory limit)
    MAX_BOOKS = 5000
    MAX_BOOK_IDS_PER_NODE = 10
    books_query = db.query(Book).filter(Book.status.in_(OWNED_STATUSES)).limit(MAX_BOOKS)
    books = books_query.all()

    # Check if we hit the limit (truncation likely occurred)
    truncated = len(books) == MAX_BOOKS

    # Build node maps
    nodes: dict[str, SocialCircleNode] = {}
    edges: dict[str, SocialCircleEdge] = {}

    # Track relationships for edge building
    author_publishers: dict[int, set[int]] = defaultdict(set)  # author_id -> publisher_ids
    publisher_authors: dict[int, set[int]] = defaultdict(set)  # publisher_id -> author_ids
    author_binders: dict[int, set[int]] = defaultdict(set)  # author_id -> binder_ids
    author_books: dict[int, list[int]] = defaultdict(list)  # author_id -> book_ids
    publisher_books: dict[int, set[int]] = defaultdict(
        set
    )  # publisher_id -> book_ids (set for O(1) lookup)
    binder_books: dict[int, set[int]] = defaultdict(
        set
    )  # binder_id -> book_ids (set for O(1) lookup)

    # First pass: collect relationships
    for book in books:
        if book.author_id:
            author_books[book.author_id].append(book.id)
            if book.publisher_id:
                author_publishers[book.author_id].add(book.publisher_id)
                publisher_authors[book.publisher_id].add(book.author_id)
                publisher_books[book.publisher_id].add(book.id)
            if book.binder_id and include_binders:
                author_binders[book.author_id].add(book.binder_id)
                binder_books[book.binder_id].add(book.id)

    # Build author nodes
    authors = db.query(Author).filter(Author.id.in_(list(author_books.keys()))).all()

    for author in authors:
        book_ids = author_books[author.id]
        if len(book_ids) < min_book_count:
            continue

        era = get_era_from_year(author.birth_year)
        if era_filter and era not in era_filter:
            continue

        node_id = f"author:{author.id}"
        nodes[node_id] = SocialCircleNode(
            id=node_id,
            entity_id=author.id,
            name=author.name,
            type=NodeType.author,
            birth_year=author.birth_year,
            death_year=author.death_year,
            era=era,
            tier=author.tier,
            book_count=len(book_ids),
            book_ids=book_ids[:MAX_BOOK_IDS_PER_NODE],
        )

    # Build publisher nodes
    publishers = db.query(Publisher).filter(Publisher.id.in_(list(publisher_books.keys()))).all()

    for publisher in publishers:
        book_ids_set = publisher_books[publisher.id]
        if len(book_ids_set) < min_book_count:
            continue

        node_id = f"publisher:{publisher.id}"
        nodes[node_id] = SocialCircleNode(
            id=node_id,
            entity_id=publisher.id,
            name=publisher.name,
            type=NodeType.publisher,
            tier=publisher.tier,
            book_count=len(book_ids_set),
            book_ids=list(book_ids_set)[:MAX_BOOK_IDS_PER_NODE],
        )

    # Build binder nodes
    if include_binders:
        binders = db.query(Binder).filter(Binder.id.in_(list(binder_books.keys()))).all()

        for binder in binders:
            book_ids_set = binder_books[binder.id]
            if len(book_ids_set) < min_book_count:
                continue

            node_id = f"binder:{binder.id}"
            nodes[node_id] = SocialCircleNode(
                id=node_id,
                entity_id=binder.id,
                name=binder.name,
                type=NodeType.binder,
                tier=binder.tier,
                book_count=len(book_ids_set),
                book_ids=list(book_ids_set)[:MAX_BOOK_IDS_PER_NODE],
            )

    # Build edges: Author -> Publisher
    for author_id, publisher_ids in author_publishers.items():
        author_node_id = f"author:{author_id}"
        if author_node_id not in nodes:
            continue

        for publisher_id in publisher_ids:
            publisher_node_id = f"publisher:{publisher_id}"
            if publisher_node_id not in nodes:
                continue

            # Find shared books using set intersection
            shared_books = list(set(author_books[author_id]) & publisher_books[publisher_id])

            edge_id = f"e:{author_node_id}:{publisher_node_id}"
            strength = max(
                2, min(len(shared_books) * 2, 10)
            )  # Scale strength, schema requires ge=2

            edges[edge_id] = SocialCircleEdge(
                id=edge_id,
                source=author_node_id,
                target=publisher_node_id,
                type=ConnectionType.publisher,
                strength=strength,
                evidence=f"Published {len(shared_books)} work(s)",
                shared_book_ids=shared_books,
            )

    # Build edges: Author <-> Author (shared publisher)
    MAX_AUTHORS_PER_PUBLISHER = 20  # Limit to prevent O(n²) explosion

    for publisher_id, author_ids in publisher_authors.items():
        publisher_node_id = f"publisher:{publisher_id}"
        if publisher_node_id not in nodes:
            continue

        author_list = sorted(author_ids, key=lambda a: len(author_books.get(a, [])), reverse=True)
        # Limit authors to prevent combinatorial explosion
        if len(author_list) > MAX_AUTHORS_PER_PUBLISHER:
            author_list = author_list[:MAX_AUTHORS_PER_PUBLISHER]

        for i, author1_id in enumerate(author_list):
            author1_node_id = f"author:{author1_id}"
            if author1_node_id not in nodes:
                continue

            for author2_id in author_list[i + 1 :]:
                author2_node_id = f"author:{author2_id}"
                if author2_node_id not in nodes:
                    continue

                # Ensure consistent edge ID ordering (use local vars to avoid corrupting loop)
                source_id, target_id = (
                    (author1_node_id, author2_node_id)
                    if author1_node_id < author2_node_id
                    else (author2_node_id, author1_node_id)
                )

                edge_id = f"e:{source_id}:{target_id}"
                if edge_id in edges:
                    continue  # Already added from another publisher

                edges[edge_id] = SocialCircleEdge(
                    id=edge_id,
                    source=source_id,
                    target=target_id,
                    type=ConnectionType.shared_publisher,
                    strength=3,  # Lower strength for indirect connection
                    evidence=f"Both published by {nodes[publisher_node_id].name}",
                )

    # Build edges: Author -> Binder
    if include_binders:
        for author_id, binder_ids in author_binders.items():
            author_node_id = f"author:{author_id}"
            if author_node_id not in nodes:
                continue

            for binder_id in binder_ids:
                binder_node_id = f"binder:{binder_id}"
                if binder_node_id not in nodes:
                    continue

                # Find shared books using set intersection
                shared_books = list(set(author_books[author_id]) & binder_books[binder_id])

                edge_id = f"e:{author_node_id}:{binder_node_id}"
                strength = max(2, min(len(shared_books) * 2, 10))  # Schema requires ge=2

                edges[edge_id] = SocialCircleEdge(
                    id=edge_id,
                    source=author_node_id,
                    target=binder_node_id,
                    type=ConnectionType.binder,
                    strength=strength,
                    evidence=f"Bound {len(shared_books)} work(s)",
                    shared_book_ids=shared_books,
                )

    # Calculate date range
    years = []
    for node in nodes.values():
        if node.birth_year:
            years.append(node.birth_year)
        if node.death_year:
            years.append(node.death_year)

    date_range = (min(years) if years else 1800, max(years) if years else 1900)

    # Build metadata
    meta = SocialCirclesMeta(
        total_books=len(books),
        total_authors=sum(1 for n in nodes.values() if n.type == NodeType.author),
        total_publishers=sum(1 for n in nodes.values() if n.type == NodeType.publisher),
        total_binders=sum(1 for n in nodes.values() if n.type == NodeType.binder),
        date_range=date_range,
        generated_at=datetime.now(UTC),
        truncated=truncated,
    )

    return SocialCirclesResponse(
        nodes=list(nodes.values()),
        edges=list(edges.values()),
        meta=meta,
    )
