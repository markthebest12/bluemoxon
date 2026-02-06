"""Wikidata portrait matching pipeline for entity profiles.

CLI wrapper that delegates to the portrait_sync service for all Wikidata/portrait
logic. This script adds CLI-specific features: argparse, NLS map fallback,
JSON-lines streaming output, and environment configuration.

For programmatic access, prefer the admin API endpoint (POST /admin/maintenance/portrait-sync)
or import from app.services.portrait_sync directly.

Usage:
    cd backend && poetry run python -m scripts.wikidata_portraits --env staging --dry-run
    cd backend && poetry run python -m scripts.wikidata_portraits --env staging --threshold 0.8
    cd backend && poetry run python -m scripts.wikidata_portraits --env staging --entity-type author
    cd backend && poetry run python -m scripts.wikidata_portraits --env staging --entity-type author --entity-id 31 --entity-id 227
"""

# ruff: noqa: T201

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.db import SessionLocal
from app.models.author import Author
from app.models.binder import Binder
from app.models.publisher import Publisher
from app.services.portrait_sync import (
    WIKIDATA_REQUEST_INTERVAL,
    process_org_entity,
    process_person_entity,
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the Wikidata portrait pipeline."""
    parser = argparse.ArgumentParser(
        description="Wikidata portrait matching pipeline for entity profiles."
    )
    parser.add_argument(
        "--env",
        choices=["staging", "production"],
        default="staging",
        help="Target environment (default: staging)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Score candidates but don't download/upload images",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.7,
        help="Minimum confidence score for a match (default: 0.7)",
    )
    parser.add_argument(
        "--entity-type",
        choices=["author", "publisher", "binder"],
        help="Process only this entity type (default: all)",
    )
    parser.add_argument(
        "--entity-id",
        type=int,
        action="append",
        help="Process only this entity ID (requires --entity-type). Can be repeated.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--skip-nls",
        action="store_true",
        help="Skip NLS historical map fallback for unmatched publishers/binders",
    )

    args = parser.parse_args()

    if args.entity_id and not args.entity_type:
        parser.error("--entity-id requires --entity-type")

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    # Set environment before loading settings
    os.environ.setdefault("BMX_ENVIRONMENT", args.env)

    get_settings()
    db = SessionLocal()

    try:
        results = []
        entity_types = [args.entity_type] if args.entity_type else ["author", "publisher", "binder"]

        for etype in entity_types:
            if etype == "author":
                query = db.query(Author)
                if args.entity_id:
                    query = query.filter(Author.id.in_(args.entity_id))
                entities = query.all()
                logger.info("Processing %d authors", len(entities))
                for entity in entities:
                    result = process_person_entity(
                        db, entity, "author", args.threshold, args.dry_run
                    )
                    results.append(result)
                    # Output JSON-line immediately
                    print(json.dumps(result))
                    time.sleep(WIKIDATA_REQUEST_INTERVAL)

            elif etype == "publisher":
                query = db.query(Publisher)
                if args.entity_id:
                    query = query.filter(Publisher.id.in_(args.entity_id))
                entities = query.all()
                logger.info("Processing %d publishers", len(entities))
                for entity in entities:
                    result = process_org_entity(
                        db, entity, "publisher", args.threshold, args.dry_run
                    )
                    results.append(result)
                    print(json.dumps(result))
                    time.sleep(WIKIDATA_REQUEST_INTERVAL)

            elif etype == "binder":
                query = db.query(Binder)
                if args.entity_id:
                    query = query.filter(Binder.id.in_(args.entity_id))
                entities = query.all()
                logger.info("Processing %d binders", len(entities))
                for entity in entities:
                    result = process_person_entity(
                        db, entity, "binder", args.threshold, args.dry_run
                    )
                    results.append(result)
                    print(json.dumps(result))
                    time.sleep(WIKIDATA_REQUEST_INTERVAL)

            # NLS map fallback for unmatched publishers/binders
            if not args.skip_nls and etype in ("publisher", "binder"):
                unmatched_statuses = {"no_results", "below_threshold", "no_portrait"}
                unmatched = [
                    r
                    for r in results
                    if r["entity_type"] == etype and r["status"] in unmatched_statuses
                ]
                if unmatched:
                    logger.info(
                        "Running NLS map fallback for %d unmatched %ss",
                        len(unmatched),
                        etype,
                    )
                    from scripts.nls_map_fallback import process_nls_fallback

                    # Build lookup of unmatched entity IDs
                    unmatched_ids = {r["entity_id"] for r in unmatched}

                    # Re-query entities for unmatched IDs
                    model_cls = Publisher if etype == "publisher" else Binder
                    nls_entities = db.query(model_cls).filter(model_cls.id.in_(unmatched_ids)).all()

                    for nls_entity in nls_entities:
                        nls_result = process_nls_fallback(
                            db, nls_entity, etype, args.dry_run, get_settings()
                        )
                        results.append(nls_result)
                        print(json.dumps(nls_result))

        # Summary to stderr
        total = len(results)
        uploaded = sum(1 for r in results if r.get("image_uploaded"))
        matched = sum(1 for r in results if r.get("score", 0) >= args.threshold)
        logger.info(
            "Pipeline complete: %d entities processed, %d matched (>= %.2f), %d portraits uploaded",
            total,
            matched,
            args.threshold,
            uploaded,
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()
