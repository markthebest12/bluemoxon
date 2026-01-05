"""Reference data services for authors, publishers, and binders."""

from sqlalchemy.orm import Session

from app.models.binder import Binder

# Binder tier mappings based on market recognition and historical significance
# Each variant maps to a canonical name. The normalization function checks for
# exact matches (case-insensitive) to avoid false positives.
TIER_1_BINDERS = {
    # Sangorski & Sutcliffe - premier 20th century bindery
    "Sangorski & Sutcliffe": "Sangorski & Sutcliffe",
    "Sangorski": "Sangorski & Sutcliffe",
    # Rivière & Son - leading Victorian/Edwardian bindery
    "Rivière & Son": "Rivière & Son",
    "Rivière": "Rivière & Son",
    "Riviere & Son": "Rivière & Son",
    "Riviere": "Rivière & Son",
    # Zaehnsdorf - prestigious Victorian bindery
    "Zaehnsdorf": "Zaehnsdorf",
    # Cobden-Sanderson / Doves Bindery - Arts & Crafts masterworks
    "Cobden-Sanderson": "Cobden-Sanderson",
    "Doves Bindery": "Cobden-Sanderson",
    "Doves": "Cobden-Sanderson",
    # Bedford - Francis Bedford, leading Victorian binder
    "Bedford": "Bedford",
    "Francis Bedford": "Bedford",
    # Hayday - James Hayday, prestigious Victorian binder
    "Hayday": "Hayday",
    "James Hayday": "Hayday",
    # Leighton - John Leighton family, top Victorian binders
    "Leighton": "Leighton",
    "J. Leighton": "Leighton",
    "John Leighton": "Leighton",
    "Leighton, Son & Hodge": "Leighton",
    # Charles Lewis - prestigious early Victorian binder
    "Charles Lewis": "Charles Lewis",
    "C. Lewis": "Charles Lewis",
    # Bayntun - moved to TIER_1 (prestigious Bath bindery, still operating)
    "Bayntun": "Bayntun",
    "Bayntun-Riviere": "Bayntun",
    "Bayntun Riviere": "Bayntun",
}

TIER_2_BINDERS = {
    # Morrell - quality Victorian/Edwardian bindery
    "Morrell": "Morrell",
    # Root & Son - good Victorian trade bindery
    "Root & Son": "Root & Son",
    "Root": "Root & Son",
    # Tout - quality Victorian trade bindery
    "Tout": "Tout",
    "Tout & Sons": "Tout",
    # Stikeman - American fine binder
    "Stikeman": "Stikeman",
    # Birdsall - quality Northampton bindery
    "Birdsall": "Birdsall",
    "Birdsall of Northampton": "Birdsall",
    "Birdsall, Northampton": "Birdsall",
    # David Bryce & Son - Scottish miniature book specialists
    "David Bryce": "David Bryce & Son",
    "Bryce": "David Bryce & Son",
    # Sotheran - primarily booksellers but quality bindings
    "Sotheran": "H. Sotheran & Co.",
    "H. Sotheran": "H. Sotheran & Co.",
    # Roger de Coverly - Arts & Crafts movement binder
    "Roger de Coverly": "Roger de Coverly",
    "de Coverly": "Roger de Coverly",
    # Cedric Chivers - known for vellucent/transparent bindings
    "Cedric Chivers": "Cedric Chivers",
    "Chivers": "Cedric Chivers",
    # Bumpus - quality London bookseller/binder
    "Bumpus": "J. & E. Bumpus",
    "J. & E. Bumpus": "J. & E. Bumpus",
    "John Bumpus": "J. & E. Bumpus",
    # Thurnam - Carlisle binder
    "Thurnam": "Thurnam",
}


def normalize_binder_name(name: str) -> tuple[str | None, str | None]:
    """Normalize binder name and determine tier.

    Args:
        name: Raw binder name from analysis

    Returns:
        Tuple of (canonical_name, tier) where tier is TIER_1, TIER_2, or None.
        Returns (None, None) for unidentified/unknown binders.
    """
    # Filter out unidentified/unknown variants (with or without parenthetical descriptions)
    # Examples: "Unidentified", "UNKNOWN", "Unidentified (no signature visible)"
    name_lower = name.lower().strip()
    if name_lower.startswith(("unidentified", "unknown", "none")):
        return None, None

    # Check Tier 1 first
    # Use exact matching (case-insensitive) to avoid false positives like:
    # - "Bedford Books Ltd" matching "Bedford" (different company contains variant)
    # - "J" matching "J. Leighton" (input is substring of variant - catastrophic!)
    # The caller is responsible for extracting the binder name from surrounding text.
    for variant, canonical in TIER_1_BINDERS.items():
        if variant.lower() == name_lower:
            return canonical, "TIER_1"

    # Check Tier 2
    for variant, canonical in TIER_2_BINDERS.items():
        if variant.lower() == name_lower:
            return canonical, "TIER_2"

    # Unknown binder - use as-is with no tier
    return name, None


def get_or_create_binder(
    db: Session,
    binder_identification: dict | None,
) -> Binder | None:
    """Look up or create a binder from parsed analysis identification.

    Args:
        db: Database session
        binder_identification: Dict with 'name', optionally 'confidence', 'evidence'

    Returns:
        Binder instance or None if no binder identified
    """
    if not binder_identification:
        return None

    name = binder_identification.get("name")
    if not name:
        return None

    # Normalize name and get tier
    canonical_name, tier = normalize_binder_name(name)

    # If normalization returned None (unidentified/unknown), don't create a binder
    if canonical_name is None:
        return None

    # Look up existing binder
    binder = db.query(Binder).filter(Binder.name == canonical_name).first()

    if binder:
        # Update tier if we have new information and current tier is null
        if tier and not binder.tier:
            binder.tier = tier
        return binder

    # Create new binder
    binder = Binder(
        name=canonical_name,
        tier=tier,
    )
    db.add(binder)
    db.flush()  # Get the ID without committing

    return binder
