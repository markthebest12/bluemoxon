"""Wikidata candidate scoring for entity portrait matching.

Scores Wikidata candidates against local entity data using multiple
signals: name similarity, year overlap, works overlap, and occupation
relevance. Used by wikidata_portraits.py to determine the best match.
"""


def name_similarity(entity_name: str, candidate_label: str) -> float:
    """Normalized token overlap similarity (0-1).

    Handles partial name matching, e.g. "Charles Dickens" vs
    "Charles John Huffam Dickens" returns 1.0 because all entity tokens
    are found in the candidate.

    Uses min denominator so that a shorter name fully contained in a
    longer name scores 1.0.
    """
    tokens_a = set(entity_name.lower().split())
    tokens_b = set(candidate_label.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    # Use min denominator for partial name matching
    return len(intersection) / min(len(tokens_a), len(tokens_b))


def year_overlap(
    entity_birth: int | None,
    entity_death: int | None,
    candidate_birth: int | None,
    candidate_death: int | None,
) -> float:
    """Score year overlap (0-1).

    Exact match both = 1.0, one exact = 0.5, within +/-5 = 0.3, else 0.
    """
    birth_match = _year_match(entity_birth, candidate_birth)
    death_match = _year_match(entity_death, candidate_death)

    if birth_match == "exact" and death_match == "exact":
        return 1.0

    score = 0.0
    if birth_match == "exact" or death_match == "exact":
        score += 0.5
    if birth_match == "close":
        score += 0.3
    if death_match == "close":
        score += 0.3
    return min(score, 1.0)


def _year_match(a: int | None, b: int | None) -> str:
    """Compare two years. Returns 'exact', 'close', or 'none'."""
    if a is None or b is None:
        return "none"
    if a == b:
        return "exact"
    if abs(a - b) <= 5:
        return "close"
    return "none"


def works_overlap(entity_book_titles: list[str], candidate_works: list[str]) -> float:
    """Jaccard similarity between book titles (0-1).

    Case-insensitive comparison with whitespace stripping.
    """
    if not entity_book_titles or not candidate_works:
        return 0.0
    set_a = {t.lower().strip() for t in entity_book_titles}
    set_b = {t.lower().strip() for t in candidate_works}
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


def occupation_match(occupations: list[str]) -> float:
    """Bonus for relevant occupation (0 or 0.3).

    Returns 0.3 if any occupation contains a book-trade-relevant term.
    """
    relevant = {"writer", "poet", "novelist", "publisher", "author", "printer", "bookbinder"}
    for occ in occupations:
        if any(r in occ.lower() for r in relevant):
            return 0.3
    return 0.0


def score_candidate(
    entity_name: str,
    entity_birth: int | None,
    entity_death: int | None,
    entity_book_titles: list[str],
    candidate_label: str,
    candidate_birth: int | None,
    candidate_death: int | None,
    candidate_works: list[str],
    candidate_occupations: list[str],
    weights: dict[str, float] | None = None,
) -> float:
    """Combined confidence score for a Wikidata candidate match.

    Default weights: name=0.35, years=0.30, works=0.20, occupation=0.15

    Returns:
        Float between 0.0 and 1.0 indicating match confidence.
    """
    w = weights or {"name": 0.35, "years": 0.30, "works": 0.20, "occupation": 0.15}

    name_score = name_similarity(entity_name, candidate_label)
    year_score = year_overlap(entity_birth, entity_death, candidate_birth, candidate_death)
    works_score = works_overlap(entity_book_titles, candidate_works)
    occ_score = occupation_match(candidate_occupations)

    return (
        w["name"] * name_score
        + w["years"] * year_score
        + w["works"] * works_score
        + w["occupation"] * occ_score
    )
