# backend/app/api/v1/social_circles.py

"""Social Circles API endpoint."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import require_viewer
from app.db import get_db
from app.schemas.social_circles import (
    Era,
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
