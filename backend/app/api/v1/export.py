"""Export API endpoints for CSV and data export."""

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Book

router = APIRouter()


@router.get("/csv")
def export_csv(
    inventory_type: str = Query(default="PRIMARY"),
    db: Session = Depends(get_db),
):
    """Export books to CSV format matching PRIMARY_COLLECTION.csv structure."""
    books = db.query(Book).filter(Book.inventory_type == inventory_type).order_by(Book.id).all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header matching PRIMARY_COLLECTION.csv format
    headers = [
        "Row",
        "Title",
        "Author",
        "Publisher",
        "Date",
        "Volumes",
        "Category",
        "Value_Low",
        "Value_Mid",
        "Value_High",
        "Purchase_Price",
        "Purchase_Date",
        "Discount_Pct",
        "ROI_Pct",
        "Status",
        "Notes",
    ]
    writer.writerow(headers)

    # Write data rows
    for i, book in enumerate(books, start=1):
        row = [
            i,
            book.title,
            book.author.name if book.author else "",
            book.publisher.name if book.publisher else "",
            book.publication_date or "",
            book.volumes,
            book.category or "",
            f"${float(book.value_low):.2f}" if book.value_low else "",
            f"${float(book.value_mid):.2f}" if book.value_mid else "",
            f"${float(book.value_high):.2f}" if book.value_high else "",
            f"${float(book.purchase_price):.2f}" if book.purchase_price else "",
            book.purchase_date.isoformat() if book.purchase_date else "",
            f"{float(book.discount_pct):.0f}%" if book.discount_pct else "",
            f"{float(book.roi_pct):.0f}%" if book.roi_pct else "",
            book.status or "ON_HAND",
            _format_notes(book),
        ]
        writer.writerow(row)

    # Reset stream position
    output.seek(0)

    # Generate filename with date
    filename = f"{inventory_type.lower()}_collection_{datetime.now().strftime('%Y%m%d')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def _format_notes(book: Book) -> str:
    """Format notes field including authenticated binder info."""
    parts = []

    # Add authenticated binder info
    if book.binding_authenticated and book.binder:
        parts.append(f"AUTHENTICATED {book.binder.name}")

    # Add binding type
    if book.binding_type:
        parts.append(book.binding_type)

    # Add condition
    if book.condition_grade:
        parts.append(f"Condition: {book.condition_grade}")

    # Add existing notes
    if book.notes:
        parts.append(book.notes)

    return "; ".join(parts) if parts else ""


@router.get("/json")
def export_json(
    inventory_type: str = Query(default="PRIMARY"),
    db: Session = Depends(get_db),
):
    """Export books to JSON format with all details."""
    books = db.query(Book).filter(Book.inventory_type == inventory_type).order_by(Book.id).all()

    return {
        "export_date": datetime.now().isoformat(),
        "inventory_type": inventory_type,
        "total_items": len(books),
        "books": [
            {
                "id": book.id,
                "title": book.title,
                "author": book.author.name if book.author else None,
                "publisher": book.publisher.name if book.publisher else None,
                "publisher_tier": book.publisher.tier if book.publisher else None,
                "binder": book.binder.name if book.binder else None,
                "binding_authenticated": book.binding_authenticated,
                "publication_date": book.publication_date,
                "year_start": book.year_start,
                "year_end": book.year_end,
                "edition": book.edition,
                "volumes": book.volumes,
                "category": book.category,
                "binding_type": book.binding_type,
                "binding_description": book.binding_description,
                "condition_grade": book.condition_grade,
                "condition_notes": book.condition_notes,
                "value_low": float(book.value_low) if book.value_low else None,
                "value_mid": float(book.value_mid) if book.value_mid else None,
                "value_high": float(book.value_high) if book.value_high else None,
                "purchase_price": float(book.purchase_price) if book.purchase_price else None,
                "purchase_date": book.purchase_date.isoformat() if book.purchase_date else None,
                "purchase_source": book.purchase_source,
                "discount_pct": float(book.discount_pct) if book.discount_pct else None,
                "roi_pct": float(book.roi_pct) if book.roi_pct else None,
                "status": book.status,
                "notes": book.notes,
                "provenance": book.provenance,
            }
            for book in books
        ],
    }
