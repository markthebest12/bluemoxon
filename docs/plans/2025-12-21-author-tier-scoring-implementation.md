# Author Tier Scoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add author tier system to align scoring with 2026 acquisition goals.

**Architecture:** Add `tier` field to Author model (matching Publisher/Binder pattern), convert tier to priority score in scoring.py, update API and frontend display.

**Tech Stack:** Python/FastAPI, SQLAlchemy, Alembic, PostgreSQL

---

## Task 1: Add tier field to Author model

**Files:**

- Modify: `backend/app/models/author.py`

**Step 1: Add tier field**

```python
# In Author class, add after priority_score line (line 22):
    tier: Mapped[str | None] = mapped_column(String(10))  # TIER_1, TIER_2, TIER_3
```

**Step 2: Verify syntax**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/author-tier-scoring/backend && poetry run python -c "from app.models.author import Author; print('OK')"`
Expected: OK

**Step 3: Commit**

```text
git add backend/app/models/author.py
git commit -m "feat(models): add tier field to Author model"
```

---

## Task 2: Create database migration

**Files:**

- Create: `backend/alembic/versions/XXXX_add_author_tier.py`

**Step 1: Generate migration**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/author-tier-scoring/backend && poetry run alembic revision --autogenerate -m "add_author_tier"`

**Step 2: Verify migration file was created**

Run: `ls -la backend/alembic/versions/ | grep author_tier`
Expected: Shows new migration file

**Step 3: Commit**

```text
git add backend/alembic/versions/
git commit -m "feat(db): add migration for author tier column"
```

---

## Task 3: Update Author schemas

**Files:**

- Modify: `backend/app/schemas/reference.py`

**Step 1: Add tier to AuthorCreate (after line 16)**

```python
    tier: str | None = None
```

**Step 2: Add tier to AuthorUpdate (after line 27)**

```python
    tier: str | None = None
```

**Step 3: Add tier to AuthorResponse (after line 39)**

```python
    tier: str | None = None
```

**Step 4: Verify syntax**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/author-tier-scoring/backend && poetry run python -c "from app.schemas.reference import AuthorCreate, AuthorUpdate, AuthorResponse; print('OK')"`
Expected: OK

**Step 5: Commit**

```text
git add backend/app/schemas/reference.py
git commit -m "feat(schemas): add tier field to Author schemas"
```

---

## Task 4: Update authors API to include tier

**Files:**

- Modify: `backend/app/api/v1/authors.py`

**Step 1: Add tier to list_authors response (line 33)**

Change from:

```python
            "priority_score": a.priority_score,
```

To:

```python
            "priority_score": a.priority_score,
            "tier": a.tier,
```

**Step 2: Add tier to AuthorResponse in create_author (after line 90)**

```python
        tier=author.tier,
```

**Step 3: Add tier to AuthorResponse in update_author (after line 121)**

```python
        tier=author.tier,
```

**Step 4: Run lint**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/author-tier-scoring/backend && poetry run ruff check app/api/v1/authors.py`
Expected: No errors

**Step 5: Commit**

```text
git add backend/app/api/v1/authors.py
git commit -m "feat(api): include tier in author API responses"
```

---

## Task 5: Add author tier to scoring calculation

**Files:**

- Modify: `backend/app/services/scoring.py`

**Step 1: Create helper function to convert tier to score (add after line 91)**

```python
def author_tier_to_score(tier: str | None) -> int:
    """Convert author tier to priority score.

    TIER_1: +15 (Darwin, Lyell - Victorian Science)
    TIER_2: +10 (Dickens, Collins - Victorian Novelists)
    TIER_3: +5 (Ruskin - Art Criticism)
    """
    if tier == "TIER_1":
        return 15
    elif tier == "TIER_2":
        return 10
    elif tier == "TIER_3":
        return 5
    return 0
```

**Step 2: Update score_book to use tier instead of priority_score**

In the score_book function around line 588, change:

```python
    author_priority = 0
```

To:

```python
    author_priority = 0
    author_tier = None
```

And around line 594, change:

```python
        author_priority = book.author.priority_score or 0
```

To:

```python
        author_tier = book.author.tier
        author_priority = author_tier_to_score(author_tier)
```

**Step 3: Run lint**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/author-tier-scoring/backend && poetry run ruff check app/services/scoring.py`
Expected: No errors

**Step 4: Commit**

```text
git add backend/app/services/scoring.py
git commit -m "feat(scoring): add author tier to scoring calculation"
```

---

## Task 6: Update scoring breakdown display

**Files:**

- Modify: `backend/app/services/scoring.py`

**Step 1: Update breakdown text (around line 446-449)**

Change from:

```python
    if author_priority_score > 0:
        score += author_priority_score
        breakdown.add(
            "author_priority",
            author_priority_score,
            f"Priority author{f' ({author_name})' if author_name else ''} - score {author_priority_score}",
        )
    elif author_name:
        breakdown.add("author_priority", 0, f"{author_name} - not a priority author")
```

To (need to pass author_tier to this function):

```python
    if author_priority_score > 0:
        score += author_priority_score
        tier_label = {"TIER_1": "Tier 1", "TIER_2": "Tier 2", "TIER_3": "Tier 3"}.get(author_tier, "Priority")
        breakdown.add(
            "author_priority",
            author_priority_score,
            f"{author_name} - {tier_label} author (+{author_priority_score})",
        )
    elif author_name:
        breakdown.add("author_priority", 0, f"{author_name} - not a priority author")
```

**Note:** This requires threading `author_tier` through the function signatures. Add `author_tier: str | None = None` parameter to:

- `calculate_strategic_fit_breakdown()` (line 330)
- `calculate_all_scores()` (line 263)
- Update calls to these functions

**Step 2: Run tests**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/author-tier-scoring/backend && poetry run pytest tests/services/test_scoring.py -v`
Expected: All tests pass

**Step 3: Commit**

```text
git add backend/app/services/scoring.py
git commit -m "feat(scoring): update breakdown to show author tier label"
```

---

## Task 7: Write tests for author tier scoring

**Files:**

- Create: `backend/tests/services/test_author_tier.py`

**Step 1: Write tests**

```python
"""Tests for author tier scoring."""

import pytest
from app.services.scoring import author_tier_to_score


class TestAuthorTierToScore:
    """Test author tier to score conversion."""

    def test_tier_1_returns_15(self):
        assert author_tier_to_score("TIER_1") == 15

    def test_tier_2_returns_10(self):
        assert author_tier_to_score("TIER_2") == 10

    def test_tier_3_returns_5(self):
        assert author_tier_to_score("TIER_3") == 5

    def test_none_returns_0(self):
        assert author_tier_to_score(None) == 0

    def test_unknown_tier_returns_0(self):
        assert author_tier_to_score("OTHER") == 0
        assert author_tier_to_score("INVALID") == 0
```

**Step 2: Run tests**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/author-tier-scoring/backend && poetry run pytest tests/services/test_author_tier.py -v`
Expected: All tests pass

**Step 3: Commit**

```text
git add backend/tests/services/test_author_tier.py
git commit -m "test: add tests for author tier scoring"
```

---

## Task 8: Apply data updates

**Files:**

- Create: `backend/alembic/versions/XXXX_seed_author_tiers.py`

**Step 1: Create data migration**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/author-tier-scoring/backend && poetry run alembic revision -m "seed_author_publisher_binder_tiers"`

**Step 2: Edit migration to add data updates**

```python
"""seed_author_publisher_binder_tiers

Revision ID: <generated>
Revises: <previous>
Create Date: <date>
"""
from alembic import op


revision = "<generated>"
down_revision = "<previous>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Author tiers
    op.execute("UPDATE authors SET tier = 'TIER_1' WHERE id = 34")  # Darwin
    op.execute("UPDATE authors SET tier = 'TIER_2' WHERE id = 250")  # Dickens
    op.execute("UPDATE authors SET tier = 'TIER_2' WHERE id = 335")  # Collins
    op.execute("UPDATE authors SET tier = 'TIER_3' WHERE id = 260")  # Ruskin

    # Create Lyell if not exists, set to TIER_1
    op.execute("""
        INSERT INTO authors (name, tier, birth_year, death_year, era)
        VALUES ('Charles Lyell', 'TIER_1', 1797, 1875, 'Victorian')
        ON CONFLICT (name) DO UPDATE SET tier = 'TIER_1'
    """)

    # Publisher tiers
    op.execute("UPDATE publishers SET tier = 'TIER_2' WHERE id = 193")  # Chatto and Windus
    op.execute("UPDATE publishers SET tier = 'TIER_2' WHERE id = 197")  # George Allen

    # Binder tiers
    op.execute("UPDATE binders SET tier = 'TIER_1' WHERE id = 4")  # Bayntun
    op.execute("UPDATE binders SET tier = 'TIER_1' WHERE id = 27")  # Leighton

    # Create Hayday binder
    op.execute("""
        INSERT INTO binders (name, tier)
        VALUES ('Hayday', 'TIER_1')
        ON CONFLICT (name) DO UPDATE SET tier = 'TIER_1'
    """)


def downgrade() -> None:
    # Revert author tiers
    op.execute("UPDATE authors SET tier = NULL WHERE id IN (34, 250, 335, 260)")
    op.execute("DELETE FROM authors WHERE name = 'Charles Lyell'")

    # Revert publisher tiers
    op.execute("UPDATE publishers SET tier = NULL WHERE id IN (193, 197)")

    # Revert binder tiers
    op.execute("UPDATE binders SET tier = 'TIER_2' WHERE id = 4")  # Bayntun was TIER_2
    op.execute("UPDATE binders SET tier = NULL WHERE id = 27")
    op.execute("DELETE FROM binders WHERE name = 'Hayday'")
```

**Step 3: Commit**

```text
git add backend/alembic/versions/
git commit -m "feat(db): add data migration for author/publisher/binder tiers"
```

---

## Task 9: Run full test suite

**Step 1: Run all backend tests**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/author-tier-scoring/backend && poetry run pytest -v`
Expected: All tests pass

**Step 2: Run linters**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/author-tier-scoring/backend && poetry run ruff check .`
Expected: No errors

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/author-tier-scoring/backend && poetry run ruff format --check .`
Expected: No formatting issues

---

## Task 10: Create PR to staging

**Step 1: Push branch**

Run: `git push -u origin feat/author-tier-scoring`

**Step 2: Create PR**

Run: `gh pr create --base staging --title "feat: Add author tier scoring (#528)" --body "## Summary

- Add tier field to Author model (TIER_1, TIER_2, TIER_3)
- Convert author tier to priority score in scoring calculation
- Update API responses to include tier
- Seed data for priority authors, publishers, binders

## Test Plan

- [ ] CI passes
- [ ] Deploy to staging
- [ ] Verify book 521 shows Darwin as Tier 1 author

Closes #528"`

**Step 3: Watch CI**

Run: `gh pr checks <pr-number> --watch`
Expected: All checks pass
