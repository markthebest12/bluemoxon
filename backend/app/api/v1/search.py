"""Search API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.db import get_db
from app.models import Book, BookAnalysis

router = APIRouter()


@router.get("")
def search(
    q: str = Query(..., min_length=1),
    scope: str = Query(default="all", pattern="^(all|books|analyses)$"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Full-text search across books and analyses."""
    results = []
    total = 0

    # Search books
    if scope in ("all", "books"):
        book_query = db.query(Book).filter(
            or_(
                Book.title.ilike(f"%{q}%"),
                Book.notes.ilike(f"%{q}%"),
                Book.binding_description.ilike(f"%{q}%"),
            )
        )
        book_count = book_query.count()
        total += book_count

        if scope == "books" or scope == "all":
            books = book_query.limit(per_page if scope == "books" else per_page // 2).all()
            for book in books:
                results.append({
                    "type": "book",
                    "id": book.id,
                    "title": book.title,
                    "author": book.author.name if book.author else None,
                    "snippet": _get_snippet(book.notes or book.binding_description or "", q),
                })

    # Search analyses
    if scope in ("all", "analyses"):
        analysis_query = db.query(BookAnalysis).filter(
            or_(
                BookAnalysis.executive_summary.ilike(f"%{q}%"),
                BookAnalysis.full_markdown.ilike(f"%{q}%"),
            )
        )
        analysis_count = analysis_query.count()
        total += analysis_count

        if scope == "analyses" or scope == "all":
            analyses = analysis_query.limit(
                per_page if scope == "analyses" else per_page // 2
            ).all()
            for analysis in analyses:
                results.append({
                    "type": "analysis",
                    "id": analysis.id,
                    "book_id": analysis.book_id,
                    "title": analysis.book.title if analysis.book else "Unknown",
                    "snippet": _get_snippet(
                        analysis.executive_summary or analysis.full_markdown or "", q
                    ),
                })

    return {
        "query": q,
        "scope": scope,
        "total": total,
        "page": page,
        "per_page": per_page,
        "results": results,
    }


def _get_snippet(text: str, query: str, context_chars: int = 100) -> str:
    """Extract a snippet around the query match."""
    if not text:
        return ""

    lower_text = text.lower()
    lower_query = query.lower()
    pos = lower_text.find(lower_query)

    if pos == -1:
        return text[:context_chars * 2] + "..." if len(text) > context_chars * 2 else text

    start = max(0, pos - context_chars)
    end = min(len(text), pos + len(query) + context_chars)

    snippet = text[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."

    return snippet
