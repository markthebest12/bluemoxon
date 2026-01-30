"""Narrative trigger classification for entity connections."""

# Minimum time span in years to qualify as cross-era bridge
CROSS_ERA_THRESHOLD = 40

# Minimum connections for hub figure classification
HUB_THRESHOLD = 5


def classify_connection(
    source_era: str | None,
    target_era: str | None,
    source_years: tuple[int | None, int | None],
    target_years: tuple[int | None, int | None],
    connection_type: str,
    source_connection_count: int,
    has_relationship_story: bool,
) -> str | None:
    """Classify a connection's narrative trigger type.

    Returns: "cross_era_bridge", "social_circle", "hub_figure", "influence_chain", or None.
    Triggers are checked in priority order (highest first).
    """
    # 1. Cross-Era Bridge
    if _is_cross_era(source_era, target_era, source_years, target_years):
        return "cross_era_bridge"

    # 2. Social Circle / Personal Relationship
    if has_relationship_story:
        return "social_circle"

    # 3. Hub Figure
    if source_connection_count >= HUB_THRESHOLD:
        return "hub_figure"

    # 4. Influence Chain (future: detect from connection metadata)
    # For now, no connections are classified as influence chains.
    # This will be enriched when relationship_story data is populated.

    return None


def _is_cross_era(
    source_era: str | None,
    target_era: str | None,
    source_years: tuple[int | None, int | None],
    target_years: tuple[int | None, int | None],
) -> bool:
    """Check if connection spans eras with sufficient time gap."""
    if not source_era or not target_era:
        return False
    if source_era == target_era:
        return False

    # Check time span using available years
    all_years = [y for y in [*source_years, *target_years] if y is not None]
    if len(all_years) < 2:
        return False

    time_span = max(all_years) - min(all_years)
    return time_span >= CROSS_ERA_THRESHOLD
