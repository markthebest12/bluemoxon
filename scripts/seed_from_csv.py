#!/usr/bin/env python3
"""Seed the database from book-collection CSV files."""

import csv
import re
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Author, Publisher, Binder, Book

# Database connection
DATABASE_URL = "postgresql://bluemoxon:bluemoxon_dev@localhost:5432/bluemoxon"

# Premium binders with their full names and authentication markers
PREMIUM_BINDERS = {
    "Zaehnsdorf": {
        "full_name": "Zaehnsdorf Ltd.",
        "markers": "Signed stamp on turn-in, gilt tooling patterns",
    },
    "Rivière": {
        "full_name": "Rivière & Son",
        "markers": "Signed on turn-in 'BOUND BY RIVIÈRE & SON'",
    },
    "Sangorski": {
        "full_name": "Sangorski & Sutcliffe",
        "markers": "Signed stamp, distinctive gilt work",
    },
    "Bayntun": {
        "full_name": "Bayntun-Riviere (George Bayntun)",
        "markers": "Signed on turn-in",
    },
}

# Book collection path
BOOK_COLLECTION = Path.home() / "projects" / "book-collection"


def parse_price(price_str: str) -> Decimal | None:
    """Parse price string like '$385.50' or '£178.65' to Decimal."""
    if not price_str or price_str.strip() == "":
        return None
    # Remove currency symbols and whitespace
    cleaned = re.sub(r"[£$,\s]", "", price_str.strip())
    # Handle ranges like "73-77%" - take first value
    if "-" in cleaned and "%" not in cleaned:
        cleaned = cleaned.split("-")[0]
    # Remove any remaining non-numeric except decimal
    cleaned = re.sub(r"[^\d.]", "", cleaned)
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def parse_percentage(pct_str: str) -> Decimal | None:
    """Parse percentage string like '73-77%' to Decimal (takes first value)."""
    if not pct_str or pct_str.strip() == "":
        return None
    # Extract first number
    match = re.search(r"(\d+(?:\.\d+)?)", pct_str)
    if match:
        try:
            return Decimal(match.group(1))
        except InvalidOperation:
            return None
    return None


def parse_date(date_str: str) -> date | None:
    """Parse date string like '2025-11-12' or '2025-11-XX'."""
    if not date_str or date_str.strip() == "":
        return None
    # Handle multiple dates (take first)
    if "+" in date_str:
        date_str = date_str.split("+")[0].strip()
    # Replace XX with 01
    date_str = re.sub(r"XX", "01", date_str)
    # Try parsing
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", date_str)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None
    return None


def parse_year_range(date_str: str) -> tuple[int | None, int | None]:
    """Parse publication date like '1867-1880' or '1851' to year range."""
    if not date_str or date_str.strip() == "":
        return None, None
    # Handle range like "1867-1880"
    range_match = re.match(r"(\d{4})\s*-\s*(\d{4})", date_str)
    if range_match:
        return int(range_match.group(1)), int(range_match.group(2))
    # Handle single year like "1851"
    single_match = re.match(r"(\d{4})", date_str)
    if single_match:
        year = int(single_match.group(1))
        return year, year
    return None, None


def normalize_status(status_str: str) -> str:
    """Normalize status to enum value."""
    if not status_str:
        return "ON_HAND"
    status_upper = status_str.upper().strip()
    if "ON HAND" in status_upper or "ON_HAND" in status_upper:
        return "ON_HAND"
    if "IN TRANSIT" in status_upper or "IN_TRANSIT" in status_upper:
        return "IN_TRANSIT"
    if "SOLD" in status_upper:
        return "SOLD"
    if "REMOVED" in status_upper or "FLAGGED" in status_upper:
        return "REMOVED"
    return "ON_HAND"


def get_or_create_author(session, name: str) -> Author | None:
    """Get or create an author by name."""
    if not name or name.strip() == "":
        return None
    name = name.strip()
    author = session.query(Author).filter(Author.name == name).first()
    if not author:
        author = Author(name=name)
        session.add(author)
        session.flush()
    return author


def get_or_create_publisher(session, name: str) -> Publisher | None:
    """Get or create a publisher by name."""
    if not name or name.strip() == "":
        return None
    name = name.strip()
    publisher = session.query(Publisher).filter(Publisher.name == name).first()
    if not publisher:
        publisher = Publisher(name=name)
        session.add(publisher)
        session.flush()
    return publisher


def get_or_create_binder(session, name: str) -> Binder | None:
    """Get or create a binder by name."""
    if not name or name.strip() == "":
        return None
    name = name.strip()
    binder = session.query(Binder).filter(Binder.name == name).first()
    if not binder:
        binder_info = PREMIUM_BINDERS.get(name, {})
        binder = Binder(
            name=name,
            full_name=binder_info.get("full_name"),
            authentication_markers=binder_info.get("markers"),
        )
        session.add(binder)
        session.flush()
    return binder


def detect_authenticated_binder(notes: str) -> str | None:
    """Detect authenticated premium binder from notes field."""
    if not notes:
        return None
    notes_upper = notes.upper()
    if "AUTHENTICATED" not in notes_upper:
        return None

    # Check for each premium binder
    for binder_name in PREMIUM_BINDERS.keys():
        if binder_name.upper() in notes_upper:
            return binder_name

    # Also check for variations
    if "SANGORSKI" in notes_upper or "SUTCLIFFE" in notes_upper or "S&S" in notes_upper:
        return "Sangorski"
    if "RIVIERE" in notes_upper or "RIVIÈRE" in notes_upper:
        return "Rivière"

    return None


def import_primary_collection(session):
    """Import PRIMARY_COLLECTION.csv."""
    csv_path = BOOK_COLLECTION / "inventory" / "PRIMARY_COLLECTION.csv"
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        return 0

    count = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip rows with empty or invalid titles (summary rows, etc.)
            title = (row.get("Title") or "").strip()
            if not title or title.startswith("TOTALS") or title.startswith("---"):
                continue

            # Get or create author/publisher
            author = get_or_create_author(session, row.get("Author", ""))
            publisher = get_or_create_publisher(session, row.get("Publisher", ""))

            # Parse year range
            year_start, year_end = parse_year_range(row.get("Date", ""))

            # Parse volumes
            try:
                volumes = int(row.get("Volumes", 1))
            except (ValueError, TypeError):
                volumes = 1

            # Detect authenticated binder from notes
            notes = row.get("Notes", "") or ""
            binder_name = detect_authenticated_binder(notes)
            binder = get_or_create_binder(session, binder_name) if binder_name else None
            binding_authenticated = binder is not None

            # Create book
            book = Book(
                title=title,
                author_id=author.id if author else None,
                publisher_id=publisher.id if publisher else None,
                binder_id=binder.id if binder else None,
                publication_date=row.get("Date", ""),
                year_start=year_start,
                year_end=year_end,
                volumes=volumes,
                category=row.get("Category", ""),
                inventory_type="PRIMARY",
                binding_authenticated=binding_authenticated,
                value_low=parse_price(row.get("Value_Low", "")),
                value_mid=parse_price(row.get("Value_Mid", "")),
                value_high=parse_price(row.get("Value_High", "")),
                purchase_price=parse_price(row.get("Purchase_Price", "")),
                purchase_date=parse_date(row.get("Purchase_Date", "")),
                discount_pct=parse_percentage(row.get("Discount_Pct", "")),
                roi_pct=parse_percentage(row.get("ROI_Pct", "")),
                status=normalize_status(row.get("Status", "")),
                notes=notes,
                legacy_row=int(row.get("Row", 0)) if row.get("Row", "").isdigit() else None,
            )
            session.add(book)
            count += 1

    return count


def import_extended_inventory(session):
    """Import EXTENDED_INVENTORY.csv."""
    csv_path = BOOK_COLLECTION / "inventory" / "EXTENDED_INVENTORY.csv"
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        return 0

    count = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip rows with empty or invalid titles
            title = (row.get("Title") or "").strip()
            if not title or title.startswith("TOTALS") or title.startswith("---"):
                continue

            # Get or create author/publisher (handle different column names)
            author_name = row.get("Author/Creator", "") or row.get("Author", "")
            author = get_or_create_author(session, author_name)
            publisher = get_or_create_publisher(session, row.get("Publisher", ""))

            # Parse year range
            year_start, year_end = parse_year_range(row.get("Date", ""))

            # Parse volumes
            try:
                volumes = int(row.get("Volumes", 1))
            except (ValueError, TypeError):
                volumes = 1

            # Calculate value_mid as average if not provided
            value_low = parse_price(row.get("Value_Low", ""))
            value_high = parse_price(row.get("Value_High", ""))
            value_mid = None
            if value_low and value_high:
                value_mid = (value_low + value_high) / 2

            # Create book
            book = Book(
                title=title,
                author_id=author.id if author else None,
                publisher_id=publisher.id if publisher else None,
                publication_date=row.get("Date", ""),
                year_start=year_start,
                year_end=year_end,
                volumes=volumes,
                category=row.get("Category", ""),
                inventory_type="EXTENDED",
                condition_grade=row.get("Condition", ""),
                value_low=value_low,
                value_mid=value_mid,
                value_high=value_high,
                provenance=row.get("Provenance_Marks", ""),
                notes=row.get("Notes", ""),
                status="ON_HAND",  # Extended inventory items are on hand
            )
            session.add(book)
            count += 1

    return count


def main():
    """Main entry point."""
    print("Connecting to database...")
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Clear existing data
        print("Clearing existing data...")
        session.query(Book).delete()
        session.query(Author).delete()
        session.query(Publisher).delete()
        session.query(Binder).delete()
        session.commit()

        # Import data
        print("Importing PRIMARY_COLLECTION.csv...")
        primary_count = import_primary_collection(session)
        print(f"  Imported {primary_count} books")

        print("Importing EXTENDED_INVENTORY.csv...")
        extended_count = import_extended_inventory(session)
        print(f"  Imported {extended_count} books")

        session.commit()

        # Summary
        total_books = session.query(Book).count()
        total_authors = session.query(Author).count()
        total_publishers = session.query(Publisher).count()
        total_binders = session.query(Binder).count()
        authenticated_count = session.query(Book).filter(Book.binding_authenticated == True).count()

        print(f"\nImport complete!")
        print(f"  Books: {total_books}")
        print(f"  Authors: {total_authors}")
        print(f"  Publishers: {total_publishers}")
        print(f"  Premium Binders: {total_binders}")
        print(f"  Authenticated Bindings: {authenticated_count}")

    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
