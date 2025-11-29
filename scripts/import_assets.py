#!/usr/bin/env python3
"""Import existing images and analysis documents from book-collection."""

import os
import re
import shutil
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Book, BookImage, BookAnalysis

# Paths
BOOK_COLLECTION = Path.home() / "projects" / "book-collection"
ASSETS_PATH = Path.home() / "projects" / "book-collection-assets"
SCREENSHOTS_PATH = ASSETS_PATH / "screenshots"
ANALYSIS_PATH = BOOK_COLLECTION / "documentation" / "book_analysis"

# Local images storage (for development)
LOCAL_IMAGES_PATH = Path(os.environ.get("LOCAL_IMAGES_PATH", "/tmp/bluemoxon-images"))

# Database connection
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://bluemoxon:bluemoxon_dev@localhost:5432/bluemoxon"
)


def normalize_title(title: str) -> str:
    """Normalize a title for matching."""
    # Remove common words and punctuation
    normalized = title.lower()
    normalized = re.sub(r'[^\w\s]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized


def extract_book_key_from_filename(filename: str) -> tuple[str, str | None, str | None]:
    """Extract book identifying info from screenshot filename.

    Format: screenshot-{BookName}_{Year}_{Details}_{Number}_{Type}.{ext}

    Returns: (book_key, year, image_type)
    """
    # Remove prefix and extension
    name = filename
    if name.startswith("screenshot-"):
        name = name[11:]
    name = Path(name).stem

    # Split by underscore
    parts = name.split("_")

    # Try to find year (4 digits)
    year = None
    year_idx = None
    for i, part in enumerate(parts):
        if re.match(r'^\d{4}$', part):
            year = part
            year_idx = i
            break

    # Book name is everything before the year
    if year_idx:
        book_name = "_".join(parts[:year_idx])
    else:
        book_name = "_".join(parts[:-2]) if len(parts) > 2 else parts[0]

    # Image type is typically the last part
    image_type = parts[-1] if len(parts) > 1 else "detail"

    # Normalize book name
    book_key = book_name.replace("_", " ").title()

    return book_key, year, image_type


def find_matching_book(session, book_key: str, year: str | None) -> Book | None:
    """Find a matching book in the database."""
    # Try exact title match first
    book = session.query(Book).filter(
        Book.title.ilike(f"%{book_key}%")
    ).first()

    if book:
        return book

    # Try normalized matching
    normalized_key = normalize_title(book_key)
    books = session.query(Book).all()

    for b in books:
        if normalized_key in normalize_title(b.title):
            return b

    return None


def import_images(session):
    """Import screenshot images to database and local storage."""
    if not SCREENSHOTS_PATH.exists():
        print(f"Screenshots path not found: {SCREENSHOTS_PATH}")
        return 0

    # Ensure local images directory exists
    LOCAL_IMAGES_PATH.mkdir(parents=True, exist_ok=True)

    count = 0
    skipped = 0
    unmatched = []

    # Group images by book
    image_groups = {}
    for img_path in SCREENSHOTS_PATH.iterdir():
        if not img_path.is_file():
            continue
        if img_path.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            continue

        book_key, year, image_type = extract_book_key_from_filename(img_path.name)
        key = (book_key, year)

        if key not in image_groups:
            image_groups[key] = []
        image_groups[key].append((img_path, image_type))

    print(f"Found {len(image_groups)} book groups in screenshots")

    for (book_key, year), images in image_groups.items():
        book = find_matching_book(session, book_key, year)

        if not book:
            unmatched.append(book_key)
            continue

        # Check if book already has images
        existing_count = session.query(BookImage).filter(
            BookImage.book_id == book.id
        ).count()

        if existing_count > 0:
            skipped += len(images)
            continue

        # Import images for this book
        for display_order, (img_path, image_type) in enumerate(sorted(images)):
            # Copy to local storage
            new_filename = f"{book.id}_{display_order:02d}_{image_type}{img_path.suffix}"
            dest_path = LOCAL_IMAGES_PATH / new_filename

            shutil.copy2(img_path, dest_path)

            # Create database record
            book_image = BookImage(
                book_id=book.id,
                s3_key=new_filename,
                image_type=image_type,
                display_order=display_order,
                is_primary=(display_order == 0),
                caption=image_type.replace("_", " ").title(),
            )
            session.add(book_image)
            count += 1

        session.flush()

    print(f"\nUnmatched books ({len(set(unmatched))}):")
    for key in sorted(set(unmatched))[:10]:
        print(f"  - {key}")
    if len(set(unmatched)) > 10:
        print(f"  ... and {len(set(unmatched)) - 10} more")

    return count, skipped


def import_analyses(session):
    """Import analysis markdown files to database."""
    if not ANALYSIS_PATH.exists():
        print(f"Analysis path not found: {ANALYSIS_PATH}")
        return 0

    count = 0
    skipped = 0
    unmatched = []

    for md_path in ANALYSIS_PATH.glob("*.md"):
        if md_path.name.startswith("README"):
            continue
        if md_path.name.startswith("PRE_"):
            continue  # Skip pre-acquisition analyses

        # Extract book info from filename
        name = md_path.stem
        if name.endswith("_analysis"):
            name = name[:-9]

        # Parse filename parts
        parts = name.split("_")

        # Try to extract meaningful parts
        # Common patterns:
        # - Title_Year_Publisher_analysis
        # - Title_Year_Author_Binder_analysis
        # - Title_Year_Binder_analysis

        # Find year
        year = None
        for part in parts:
            if re.match(r'^\d{4}$', part):
                year = part
                break

        # Build search key from first few parts
        if len(parts) >= 2:
            search_key = " ".join(parts[:2])
        else:
            search_key = parts[0]

        # Find matching book
        book = find_matching_book(session, search_key, year)

        if not book:
            # Try with more parts
            if len(parts) >= 3:
                search_key = " ".join(parts[:3])
                book = find_matching_book(session, search_key, year)

        if not book:
            unmatched.append(name)
            continue

        # Check if book already has analysis
        if book.analysis:
            skipped += 1
            continue

        # Read markdown content
        content = md_path.read_text(encoding="utf-8")

        # Create analysis record
        analysis = BookAnalysis(
            book_id=book.id,
            full_markdown=content,
            source_filename=md_path.name,
        )

        # Try to extract executive summary (first paragraph after title)
        lines = content.split("\n")
        summary_lines = []
        in_summary = False
        for line in lines:
            if line.startswith("# "):
                in_summary = True
                continue
            if in_summary:
                if line.startswith("#"):
                    break
                if line.strip():
                    summary_lines.append(line.strip())
                if len(summary_lines) >= 3:
                    break

        if summary_lines:
            analysis.executive_summary = " ".join(summary_lines)[:500]

        session.add(analysis)
        count += 1

    print(f"\nUnmatched analyses ({len(unmatched)}):")
    for name in sorted(unmatched)[:10]:
        print(f"  - {name}")
    if len(unmatched) > 10:
        print(f"  ... and {len(unmatched) - 10} more")

    return count, skipped


def main():
    """Main entry point."""
    print("Connecting to database...")
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        print("\n=== Importing Images ===")
        img_count, img_skipped = import_images(session)
        print(f"  Imported: {img_count}")
        print(f"  Skipped (already exists): {img_skipped}")

        print("\n=== Importing Analyses ===")
        ana_count, ana_skipped = import_analyses(session)
        print(f"  Imported: {ana_count}")
        print(f"  Skipped (already exists): {ana_skipped}")

        session.commit()

        # Summary
        total_images = session.query(BookImage).count()
        total_analyses = session.query(BookAnalysis).count()
        books_with_images = session.query(Book).filter(
            Book.images.any()
        ).count()
        books_with_analyses = session.query(Book).filter(
            Book.analysis != None
        ).count()

        print("\n=== Import Complete ===")
        print(f"  Total images in database: {total_images}")
        print(f"  Total analyses in database: {total_analyses}")
        print(f"  Books with images: {books_with_images}")
        print(f"  Books with analyses: {books_with_analyses}")

    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
