#!/usr/bin/env python3
"""
One-time script to clean up book titles by removing embedded years and volume counts.
These are redundant since they exist in separate database columns.

Run from bluemoxon/backend directory:
    poetry run python ../scripts/update_titles.py

Or with the API directly (requires auth token):
    python scripts/update_titles.py --api --token YOUR_TOKEN
"""

import argparse
import sys
from pathlib import Path

# Title mappings: old_title -> new_title
TITLE_UPDATES = {
    "Tennyson Complete Poetical Works (Moxon 9-vol)": "Tennyson Complete Poetical Works (Moxon)",
    "Byron Complete Poetical Works (Murray 8-vol)": "Byron Complete Poetical Works (Murray)",
    "The Popular Educator (Cassell 1870s)": "The Popular Educator (Cassell)",
    "Masters in Art 6 vols Bates & Guild": "Masters in Art",
    "Dickens Works 3 vols 1880s": "Dickens Works",
}

# Book IDs in production database (from search results)
BOOK_IDS = {
    335: "Tennyson Complete Poetical Works (Moxon)",
    336: "Byron Complete Poetical Works (Murray)",
    345: "The Popular Educator (Cassell)",
    376: "Masters in Art",
    377: "Dickens Works",
}


def update_via_sqlalchemy():
    """Update titles using SQLAlchemy (requires running from backend dir)."""
    # Add backend to path
    backend_path = Path(__file__).parent.parent / "backend"
    sys.path.insert(0, str(backend_path))

    try:
        from app.db import SessionLocal
        from app.models import Book
    except ImportError:
        print("Error: Could not import app modules.")
        print("Make sure you run this from the backend directory:")
        print("  cd backend && poetry run python ../scripts/update_titles.py")
        return False

    db = SessionLocal()
    try:
        updated = 0
        for book_id, new_title in BOOK_IDS.items():
            book = db.query(Book).filter(Book.id == book_id).first()
            if book:
                old_title = book.title
                if old_title != new_title:
                    book.title = new_title
                    print(f"Updated ID {book_id}: '{old_title}' -> '{new_title}'")
                    updated += 1
                else:
                    print(f"Skipped ID {book_id}: already has correct title")
            else:
                print(f"Warning: Book ID {book_id} not found")

        if updated > 0:
            db.commit()
            print(f"\nCommitted {updated} updates to database.")
        else:
            print("\nNo updates needed.")
        return True
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        return False
    finally:
        db.close()


def update_via_api(token: str, base_url: str = "https://api.bluemoxon.com"):
    """Update titles using the REST API."""
    import requests

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    updated = 0
    for book_id, new_title in BOOK_IDS.items():
        url = f"{base_url}/api/v1/books/{book_id}"

        # First get current title
        resp = requests.get(url)
        if resp.status_code != 200:
            print(f"Warning: Could not fetch book {book_id}: {resp.status_code}")
            continue

        current = resp.json()
        old_title = current.get("title")

        if old_title == new_title:
            print(f"Skipped ID {book_id}: already has correct title")
            continue

        # Update
        resp = requests.put(url, json={"title": new_title}, headers=headers)
        if resp.status_code == 200:
            print(f"Updated ID {book_id}: '{old_title}' -> '{new_title}'")
            updated += 1
        else:
            print(f"Error updating {book_id}: {resp.status_code} - {resp.text}")

    print(f"\nUpdated {updated} books via API.")
    return updated > 0


def main():
    parser = argparse.ArgumentParser(description="Update book titles to remove redundant years/volumes")
    parser.add_argument("--api", action="store_true", help="Use REST API instead of direct DB")
    parser.add_argument("--token", help="Auth token for API calls")
    parser.add_argument("--url", default="https://api.bluemoxon.com", help="API base URL")
    args = parser.parse_args()

    print("Title Update Script")
    print("=" * 50)
    print(f"Updates to apply: {len(BOOK_IDS)}")
    print()

    if args.api:
        if not args.token:
            print("Error: --token required when using --api")
            sys.exit(1)
        success = update_via_api(args.token, args.url)
    else:
        success = update_via_sqlalchemy()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
