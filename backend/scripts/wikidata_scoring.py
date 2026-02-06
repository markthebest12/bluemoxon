"""DEPRECATED: Canonical module is app.utils.wikidata_scoring.

This shim re-exports for backwards compatibility with scripts that run
outside the Lambda deployment package. All new code should import from
app.utils.wikidata_scoring directly.
"""

from app.utils.wikidata_scoring import (  # noqa: F401
    name_similarity,
    occupation_match,
    score_candidate,
    works_overlap,
    year_overlap,
)
