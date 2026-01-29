# backend/app/api/v1/social_circles.py

"""Social Circles API endpoint."""

import time

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import require_viewer
from app.db import get_db
from app.schemas.social_circles import (
    ConnectionType,
    Era,
    NodeType,
    SocialCirclesResponse,
)
from app.services.social_circles import build_social_circles_graph

router = APIRouter()


@router.get(
    "/",
    response_model=SocialCirclesResponse,
    summary="Get social circles network graph",
    description="""
    Returns a network graph of connections between authors, publishers,
    and binders based on the book collection.

    Connections are inferred from:
    - **publisher**: Author was published by a publisher
    - **shared_publisher**: Two authors share the same publisher
    - **binder**: Author's book was bound by a binder
    """,
)
def get_social_circles(
    include_binders: bool = Query(
        True,
        description="Include binder nodes and edges in the graph",
    ),
    min_book_count: int = Query(
        1,
        ge=1,
        le=100,
        description="Minimum books for an entity to be included (max 100)",
    ),
    max_books: int = Query(
        5000,
        ge=100,
        le=10000,
        description="Maximum books to process (100-10000, default 5000)",
    ),
    era: list[Era] | None = Query(
        None,
        description="Filter nodes by historical era(s)",
    ),
    db: Session = Depends(get_db),
    _user_info=Depends(require_viewer),
) -> SocialCirclesResponse:
    """Get the social circles network graph."""
    return build_social_circles_graph(
        db=db,
        include_binders=include_binders,
        min_book_count=min_book_count,
        max_books=max_books,
        era_filter=era,
    )


@router.get(
    "/health",
    summary="Social circles health check",
    description="Validates data integrity and query performance for social circles.",
)
def social_circles_health(
    db: Session = Depends(get_db),
    _user_info=Depends(require_viewer),
):
    """Deep health check for social circles feature."""
    start = time.monotonic()

    try:
        # Build graph to measure performance (use smaller limit for health check)
        result = build_social_circles_graph(db, max_books=1000)
        build_time = (time.monotonic() - start) * 1000

        # Count nodes by type
        node_counts = {
            "authors": sum(1 for n in result.nodes if n.type == NodeType.author),
            "publishers": sum(1 for n in result.nodes if n.type == NodeType.publisher),
            "binders": sum(1 for n in result.nodes if n.type == NodeType.binder),
        }

        # Count edges by type
        edge_counts = {
            "publisher": sum(1 for e in result.edges if e.type == ConnectionType.publisher),
            "shared_publisher": sum(
                1 for e in result.edges if e.type == ConnectionType.shared_publisher
            ),
            "binder": sum(1 for e in result.edges if e.type == ConnectionType.binder),
        }

        # Determine health status
        perf_healthy = build_time < 500  # Under 500ms threshold
        data_healthy = node_counts["authors"] > 0 or node_counts["publishers"] > 0

        if perf_healthy and data_healthy:
            status = "healthy"
        elif data_healthy:
            status = "degraded"
        else:
            status = "unhealthy"

        return {
            "status": status,
            "latency_ms": round(build_time, 2),
            "checks": {
                "node_counts": {
                    "status": "healthy" if data_healthy else "unhealthy",
                    **node_counts,
                },
                "edge_counts": {
                    "status": "healthy",
                    **edge_counts,
                },
                "query_performance": {
                    "status": "healthy" if perf_healthy else "degraded",
                    "build_time_ms": round(build_time, 2),
                    "threshold_ms": 500,
                },
            },
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": round((time.monotonic() - start) * 1000, 2),
            "checks": {},
        }
