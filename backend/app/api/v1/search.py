"""Search API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models import Book, BookAnalysis

router = APIRouter()

# Max results per type when combining (prevents memory bomb on broad searches)
_MAX_COMBINED_RESULTS_PER_TYPE = 500


@router.get("")
def search(
    q: str = Query(..., min_length=1),
    scope: str = Query(default="all", pattern="^(all|books|analyses)$"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Full-text search across books and analyses.

    Note: Total count is computed before fetching results. In rare cases with
    concurrent modifications, the actual result count may differ slightly.
    """
    offset = (page - 1) * per_page
    results = []
    total = 0

    # Build book query with eager loading and deterministic ordering
    book_query = None
    if scope in ("all", "books"):
        book_query = (
            db.query(Book)
            .options(joinedload(Book.author))
            .filter(
                or_(
                    Book.title.ilike(f"%{q}%"),
                    Book.notes.ilike(f"%{q}%"),
                    Book.binding_description.ilike(f"%{q}%"),
                )
            )
            .order_by(Book.id)
        )
        total += book_query.count()

    # Build analysis query with eager loading and deterministic ordering
    analysis_query = None
    if scope in ("all", "analyses"):
        analysis_query = (
            db.query(BookAnalysis)
            .options(joinedload(BookAnalysis.book))
            .filter(
                or_(
                    BookAnalysis.executive_summary.ilike(f"%{q}%"),
                    BookAnalysis.full_markdown.ilike(f"%{q}%"),
                )
            )
            .order_by(BookAnalysis.id)
        )
        total += analysis_query.count()

    # Handle pagination based on scope
    if scope == "books":
        books = book_query.offset(offset).limit(per_page).all()
        for book in books:
            results.append(_book_to_result(book, q))

    elif scope == "analyses":
        analyses = analysis_query.offset(offset).limit(per_page).all()
        for analysis in analyses:
            results.append(_analysis_to_result(analysis, q))

    else:
        # scope == "all": Combine results, then paginate in memory
        # Cap results per type to prevent memory issues on broad searches
        all_results = []
        if book_query:
            for book in book_query.limit(_MAX_COMBINED_RESULTS_PER_TYPE).all():
                all_results.append(_book_to_result(book, q))
        if analysis_query:
            for analysis in analysis_query.limit(_MAX_COMBINED_RESULTS_PER_TYPE).all():
                all_results.append(_analysis_to_result(analysis, q))

        # Apply pagination to combined results
        results = all_results[offset : offset + per_page]

    return {
        "query": q,
        "scope": scope,
        "total": total,
        "page": page,
        "per_page": per_page,
        "results": results,
    }


def _book_to_result(book: Book, q: str) -> dict:
    """Convert a Book to a search result dict."""
    return {
        "type": "book",
        "id": book.id,
        "title": book.title,
        "author": book.author.name if book.author else None,
        "snippet": _get_snippet(book.notes or book.binding_description or "", q),
    }


def _analysis_to_result(analysis: BookAnalysis, q: str) -> dict:
    """Convert a BookAnalysis to a search result dict."""
    return {
        "type": "analysis",
        "id": analysis.id,
        "book_id": analysis.book_id,
        "title": analysis.book.title if analysis.book else "Unknown",
        "snippet": _get_snippet(analysis.executive_summary or analysis.full_markdown or "", q),
    }


def _get_snippet(text: str, query: str, context_chars: int = 100) -> str:
    """Extract a snippet around the query match."""
    if not text:
        return ""

    lower_text = text.lower()
    lower_query = query.lower()
    pos = lower_text.find(lower_query)

    if pos == -1:
        return text[: context_chars * 2] + "..." if len(text) > context_chars * 2 else text

    start = max(0, pos - context_chars)
    end = min(len(text), pos + len(query) + context_chars)

    snippet = text[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."

    return snippet
