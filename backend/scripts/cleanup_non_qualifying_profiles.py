#!/usr/bin/env python3
"""Cleanup script to remove social circles data for non-qualifying books (#1866).

Removes entity_profiles and ai_connections for entities that no longer have
any qualifying (IN_TRANSIT or ON_HAND) books. This is a one-time operation
to clean up data created before the scope restriction was implemented.

Usage:
    # Dry run (no changes):
    python backend/scripts/cleanup_non_qualifying_profiles.py --dry-run

    # Execute cleanup:
    python backend/scripts/cleanup_non_qualifying_profiles.py --execute
"""

# ruff: noqa: T201

import argparse
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove social circles data for non-qualifying books (#1866)"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Preview changes without executing")
    group.add_argument("--execute", action="store_true", help="Execute the cleanup")
    args = parser.parse_args()

    # Lazy imports to avoid loading the full app at module level
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.config import get_settings
    from app.enums import OWNED_STATUSES
    from app.models.ai_connection import AIConnection
    from app.models.book import Book
    from app.models.entity_profile import EntityProfile

    settings = get_settings()
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        owned_values = [s.value for s in OWNED_STATUSES]
        print(f"Qualifying statuses: {owned_values}")
        print("-" * 60)

        # Find entity_profiles whose entities have no qualifying books
        profiles = db.query(EntityProfile).all()
        stale_profiles: list[EntityProfile] = []

        fk_map = {
            "author": "author_id",
            "publisher": "publisher_id",
            "binder": "binder_id",
        }

        for profile in profiles:
            fk_col = fk_map.get(profile.entity_type)
            if not fk_col:
                continue

            owned_count = (
                db.query(Book)
                .filter(
                    getattr(Book, fk_col) == profile.entity_id,
                    Book.status.in_(owned_values),
                )
                .count()
            )

            if owned_count == 0:
                stale_profiles.append(profile)

        print(f"Entity profiles to remove: {len(stale_profiles)}")
        for p in stale_profiles:
            print(f"  - {p.entity_type}:{p.entity_id} (profile ID {p.id})")

        # Find AI connections where either endpoint has no qualifying books
        ai_connections = db.query(AIConnection).all()
        stale_connections: list[AIConnection] = []

        for conn in ai_connections:
            # Check source
            src_fk = fk_map.get(conn.source_type)
            tgt_fk = fk_map.get(conn.target_type)

            src_ok = False
            tgt_ok = False

            if src_fk:
                src_ok = (
                    db.query(Book)
                    .filter(
                        getattr(Book, src_fk) == conn.source_id,
                        Book.status.in_(owned_values),
                    )
                    .count()
                    > 0
                )
            if tgt_fk:
                tgt_ok = (
                    db.query(Book)
                    .filter(
                        getattr(Book, tgt_fk) == conn.target_id,
                        Book.status.in_(owned_values),
                    )
                    .count()
                    > 0
                )

            if not src_ok or not tgt_ok:
                stale_connections.append(conn)

        print(f"AI connections to remove: {len(stale_connections)}")
        for c in stale_connections:
            print(
                f"  - {c.source_type}:{c.source_id} -> "
                f"{c.target_type}:{c.target_id} ({c.relationship})"
            )

        if args.dry_run:
            print("\nDRY RUN - No changes made.")
            return

        # Execute cleanup
        if stale_profiles:
            for p in stale_profiles:
                db.delete(p)
            print(f"\nDeleted {len(stale_profiles)} entity profiles.")

        if stale_connections:
            for c in stale_connections:
                db.delete(c)
            print(f"Deleted {len(stale_connections)} AI connections.")

        db.commit()
        print("\nCleanup complete.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
