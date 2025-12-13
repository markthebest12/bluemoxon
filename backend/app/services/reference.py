"""Reference data services for authors, publishers, and binders."""

from sqlalchemy.orm import Session

from app.models.binder import Binder


# Binder tier mappings based on market recognition and historical significance
TIER_1_BINDERS = {
    "Sangorski & Sutcliffe": "Sangorski & Sutcliffe",
    "Sangorski": "Sangorski & Sutcliffe",
    "Rivière & Son": "Rivière & Son",
    "Rivière": "Rivière & Son",
    "Riviere & Son": "Rivière & Son",
    "Riviere": "Rivière & Son",
    "Zaehnsdorf": "Zaehnsdorf",
    "Cobden-Sanderson": "Cobden-Sanderson",
    "Doves Bindery": "Cobden-Sanderson",
    "Bedford": "Bedford",
}

TIER_2_BINDERS = {
    "Morrell": "Morrell",
    "Root & Son": "Root & Son",
    "Root": "Root & Son",
    "Bayntun": "Bayntun",
    "Bayntun-Riviere": "Bayntun",
    "Tout": "Tout",
    "Stikeman": "Stikeman",
}


def normalize_binder_name(name: str) -> tuple[str, str | None]:
    """Normalize binder name and determine tier.

    Args:
        name: Raw binder name from analysis

    Returns:
        Tuple of (canonical_name, tier) where tier is TIER_1, TIER_2, or None
    """
    # Check Tier 1 first
    for variant, canonical in TIER_1_BINDERS.items():
        if variant.lower() in name.lower() or name.lower() in variant.lower():
            return canonical, "TIER_1"

    # Check Tier 2
    for variant, canonical in TIER_2_BINDERS.items():
        if variant.lower() in name.lower() or name.lower() in variant.lower():
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
