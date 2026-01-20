"""Application constants."""

# Analysis model configuration
# Default model for Napoleon analysis generation
DEFAULT_ANALYSIS_MODEL = "opus"

# Era definitions with year ranges and descriptions
# Single source of truth - frontend fetches these from /api/v1/references/eras
ERA_DEFINITIONS: dict[str, dict[str, str]] = {
    "Pre-Romantic (before 1800)": {
        "label": "Pre-Romantic",
        "years": "Before 1800",
        "description": "Works published before the Romantic period",
    },
    "Romantic (1800-1836)": {
        "label": "Romantic",
        "years": "1800-1836",
        "description": "The Romantic era, featuring Wordsworth, Coleridge, Byron, Shelley, Keats",
    },
    "Victorian (1837-1901)": {
        "label": "Victorian",
        "years": "1837-1901",
        "description": "Queen Victoria's reign, the golden age of British publishing",
    },
    "Edwardian (1902-1910)": {
        "label": "Edwardian",
        "years": "1902-1910",
        "description": "King Edward VII's reign, continuation of Victorian traditions",
    },
    "Post-1910": {
        "label": "Post-1910",
        "years": "After 1910",
        "description": "Modern era, after the Edwardian period",
    },
    "Unknown": {
        "label": "Unknown",
        "years": "No date",
        "description": "Books without a recorded publication date",
    },
}

# Condition grade definitions (ABAA standard)
# Single source of truth - frontend fetches these from /api/v1/references/conditions
CONDITION_GRADE_DEFINITIONS: dict[str, dict[str, str]] = {
    "FINE": {"label": "Fine", "description": "Nearly as new, no defects"},
    "NEAR_FINE": {"label": "Near Fine", "description": "Approaching fine, very minor defects"},
    "VERY_GOOD": {"label": "Very Good", "description": "Worn but untorn, minimum for collectors"},
    "GOOD": {"label": "Good", "description": "Average used, regular wear"},
    "FAIR": {"label": "Fair", "description": "Wear and tear, but complete"},
    "POOR": {"label": "Poor", "description": "Heavily damaged, reading copy only"},
}
