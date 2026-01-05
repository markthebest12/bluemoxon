# Publisher Aliases Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace hardcoded TIER_1_PUBLISHERS/TIER_2_PUBLISHERS dicts with a database-backed publisher_aliases table.

**Architecture:** New `publisher_aliases` table maps variant names to canonical publishers. The `normalize_publisher_name()` function queries this table instead of hardcoded dicts. Migration seeds all existing variant mappings.

**Tech Stack:** SQLAlchemy, Alembic, PostgreSQL, pytest

---

## Task 1: Create PublisherAlias Model

**Files:**
- Create: `backend/app/models/publisher_alias.py`
- Modify: `backend/app/models/__init__.py`

**Step 1: Write the model file**

```python
"""Publisher alias model for name variant mappings."""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PublisherAlias(Base):
    """Maps publisher name variants to canonical publishers."""

    __tablename__ = "publisher_aliases"

    id: Mapped[int] = mapped_column(primary_key=True)
    alias_name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    publisher_id: Mapped[int] = mapped_column(ForeignKey("publishers.id", ondelete="CASCADE"), nullable=False)

    publisher = relationship("Publisher", back_populates="aliases")
```

**Step 2: Add relationship to Publisher model**

In `backend/app/models/publisher.py`, add to Publisher class:
```python
aliases = relationship("PublisherAlias", back_populates="publisher", cascade="all, delete-orphan")
```

**Step 3: Export in __init__.py**

In `backend/app/models/__init__.py`, add:
```python
from app.models.publisher_alias import PublisherAlias
```

**Step 4: Commit**

```bash
git add backend/app/models/publisher_alias.py backend/app/models/publisher.py backend/app/models/__init__.py
git commit -m "feat(models): add PublisherAlias model for name variant mappings"
```

---

## Task 2: Create Migration with Seed Data

**Files:**
- Create: `backend/alembic/versions/YYYYMMDD_add_publisher_aliases.py`

**Step 1: Generate migration skeleton**

Run: `cd backend && poetry run alembic revision -m "add_publisher_aliases_table"`

**Step 2: Write migration with seed data**

```python
"""Add publisher_aliases table with seed data.

Revision ID: [auto-generated]
Revises: [auto-generated]
Create Date: [auto-generated]
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "[auto-generated]"
down_revision = "[auto-generated]"
branch_labels = None
depends_on = None

# Seed data: (canonical_name, tier, [aliases])
PUBLISHER_SEEDS = [
    # Tier 1
    ("Macmillan and Co.", "TIER_1", ["Macmillan"]),
    ("Chapman & Hall", "TIER_1", ["Chapman and Hall"]),
    ("Smith, Elder & Co.", "TIER_1", ["Smith Elder"]),
    ("John Murray", "TIER_1", ["Murray"]),
    ("William Blackwood and Sons", "TIER_1", ["Blackwood"]),
    ("Edward Moxon and Co.", "TIER_1", ["Moxon"]),
    ("Oxford University Press", "TIER_1", ["OUP"]),
    ("Clarendon Press", "TIER_1", []),
    ("Longmans, Green & Co.", "TIER_1", ["Longmans", "Longman"]),
    ("Harper & Brothers", "TIER_1", ["Harper"]),
    ("D. Appleton and Company", "TIER_1", ["Appleton"]),
    ("Little, Brown, and Company", "TIER_1", ["Little Brown"]),
    ("Richard Bentley", "TIER_1", ["Bentley"]),
    # Tier 2
    ("Chatto and Windus", "TIER_2", ["Chatto & Windus"]),
    ("George Allen", "TIER_2", []),
    ("Cassell, Petter & Galpin", "TIER_2", ["Cassell"]),
    ("Routledge", "TIER_2", []),
    ("Ward, Lock & Co.", "TIER_2", ["Ward Lock"]),
    ("Hurst & Company", "TIER_2", []),
    ("Grosset & Dunlap", "TIER_2", []),
]


def upgrade() -> None:
    # Create table
    op.create_table(
        "publisher_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alias_name", sa.String(length=200), nullable=False),
        sa.Column("publisher_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["publisher_id"], ["publishers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_publisher_aliases_alias_name", "publisher_aliases", ["alias_name"], unique=True)

    # Seed data using raw SQL for reliability
    conn = op.get_bind()

    for canonical_name, tier, aliases in PUBLISHER_SEEDS:
        # Upsert publisher
        result = conn.execute(
            sa.text("SELECT id FROM publishers WHERE name = :name"),
            {"name": canonical_name},
        )
        row = result.fetchone()

        if row:
            publisher_id = row[0]
            # Update tier if needed
            conn.execute(
                sa.text("UPDATE publishers SET tier = :tier WHERE id = :id AND (tier IS NULL OR tier != :tier)"),
                {"tier": tier, "id": publisher_id},
            )
        else:
            result = conn.execute(
                sa.text("INSERT INTO publishers (name, tier, preferred) VALUES (:name, :tier, false) RETURNING id"),
                {"name": canonical_name, "tier": tier},
            )
            publisher_id = result.fetchone()[0]

        # Insert canonical name as alias (for consistent lookup)
        conn.execute(
            sa.text(
                "INSERT INTO publisher_aliases (alias_name, publisher_id) VALUES (:alias, :pub_id) "
                "ON CONFLICT (alias_name) DO NOTHING"
            ),
            {"alias": canonical_name, "pub_id": publisher_id},
        )

        # Insert variant aliases
        for alias in aliases:
            conn.execute(
                sa.text(
                    "INSERT INTO publisher_aliases (alias_name, publisher_id) VALUES (:alias, :pub_id) "
                    "ON CONFLICT (alias_name) DO NOTHING"
                ),
                {"alias": alias, "pub_id": publisher_id},
            )


def downgrade() -> None:
    op.drop_index("ix_publisher_aliases_alias_name", table_name="publisher_aliases")
    op.drop_table("publisher_aliases")
```

**Step 3: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat(migration): add publisher_aliases table with seed data"
```

---

## Task 3: Write Tests for DB-backed normalize_publisher_name

**Files:**
- Modify: `backend/tests/test_publisher_validation.py`

**Step 1: Update TestNormalizePublisherName to use db fixture**

The tests need to:
1. Accept `db` fixture
2. Seed aliases in the test db
3. Call `normalize_publisher_name(db, name)` with db session

```python
class TestNormalizePublisherName:
    """Test publisher name normalization and tier assignment."""

    @pytest.fixture(autouse=True)
    def seed_aliases(self, db):
        """Seed publisher aliases for tests."""
        from app.models.publisher import Publisher
        from app.models.publisher_alias import PublisherAlias

        # Create publishers with tiers
        publishers_data = [
            ("Macmillan and Co.", "TIER_1", ["Macmillan"]),
            ("Chapman & Hall", "TIER_1", ["Chapman and Hall"]),
            ("Smith, Elder & Co.", "TIER_1", ["Smith Elder"]),
            ("John Murray", "TIER_1", ["Murray"]),
            ("Oxford University Press", "TIER_1", ["OUP"]),
            ("Longmans, Green & Co.", "TIER_1", ["Longmans", "Longman"]),
            ("Harper & Brothers", "TIER_1", ["Harper"]),
            ("Chatto and Windus", "TIER_2", ["Chatto & Windus"]),
            ("George Allen", "TIER_2", []),
        ]

        for name, tier, aliases in publishers_data:
            pub = Publisher(name=name, tier=tier)
            db.add(pub)
            db.flush()
            # Add canonical name as alias
            db.add(PublisherAlias(alias_name=name, publisher_id=pub.id))
            for alias in aliases:
                db.add(PublisherAlias(alias_name=alias, publisher_id=pub.id))
        db.flush()

    def test_tier_1_macmillan(self, db):
        name, tier = normalize_publisher_name(db, "Macmillan and Co.")
        assert name == "Macmillan and Co."
        assert tier == "TIER_1"

    # ... update all other tests to pass db as first arg
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && poetry run pytest tests/test_publisher_validation.py::TestNormalizePublisherName -v`
Expected: FAIL (normalize_publisher_name doesn't accept db yet)

**Step 3: Commit test changes**

```bash
git add backend/tests/test_publisher_validation.py
git commit -m "test: update normalize_publisher_name tests for db-backed lookup"
```

---

## Task 4: Implement DB-backed normalize_publisher_name

**Files:**
- Modify: `backend/app/services/publisher_validation.py`

**Step 1: Update normalize_publisher_name signature and implementation**

```python
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.publisher_alias import PublisherAlias


def normalize_publisher_name(db: Session, name: str) -> tuple[str, str | None]:
    """Normalize publisher name and determine tier from database.

    Applies auto-correction rules first, then looks up alias in database.

    Args:
        db: Database session
        name: Raw publisher name from analysis

    Returns:
        Tuple of (canonical_name, tier) where tier is TIER_1, TIER_2, or None
    """
    # Apply auto-correction first
    corrected = auto_correct_publisher_name(name)

    # Look up alias in database (case-insensitive)
    alias = (
        db.query(PublisherAlias)
        .filter(func.lower(PublisherAlias.alias_name) == corrected.lower())
        .first()
    )

    if alias:
        return alias.publisher.name, alias.publisher.tier

    # Unknown publisher - return corrected name with no tier
    return corrected, None
```

**Step 2: Remove hardcoded TIER_1_PUBLISHERS and TIER_2_PUBLISHERS dicts**

Delete lines 100-143 (the two dict definitions).

**Step 3: Update get_or_create_publisher to pass db to normalize_publisher_name**

Line 259 already calls it correctly since it has db in scope.

**Step 4: Run tests**

Run: `cd backend && poetry run pytest tests/test_publisher_validation.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/publisher_validation.py
git commit -m "feat: implement db-backed normalize_publisher_name"
```

---

## Task 5: Remove Dead Code from stats.py

**Files:**
- Modify: `backend/app/api/v1/stats.py`

**Step 1: Delete TIER_1_PUBLISHERS constant**

Delete lines 15-23 (the unused list).

**Step 2: Run linter to verify no issues**

Run: `cd backend && poetry run ruff check app/api/v1/stats.py`
Expected: No errors

**Step 3: Commit**

```bash
git add backend/app/api/v1/stats.py
git commit -m "refactor: remove dead TIER_1_PUBLISHERS constant from stats.py"
```

---

## Task 6: Run Full Test Suite

**Step 1: Run all backend tests**

Run: `cd backend && poetry run pytest -v`
Expected: All tests pass

**Step 2: Run linter on all files**

Run: `cd backend && poetry run ruff check .`
Expected: No errors

**Step 3: Run formatter check**

Run: `cd backend && poetry run ruff format --check .`
Expected: No formatting issues

---

## Task 7: Create PR to Staging

**Step 1: Create feature branch if not already on one**

Run: `git checkout -b refactor/publisher-aliases-803`

**Step 2: Push and create PR**

Run: `git push -u origin refactor/publisher-aliases-803`

Create PR targeting `staging` branch with title:
`refactor: Move TIER_1_PUBLISHERS to database (closes #803)`

**Step 3: Wait for CI and user review**

---

## Task 8: After Staging Validation, Promote to Production

**Step 1: Create PR from staging to main**

After staging validation, create PR to promote changes to production.

---

## Parallel Execution Notes

**Tasks that can run in parallel:**
- Task 1 (model) and Task 2 (migration) can be developed together
- Task 3 (tests) depends on Task 1
- Task 4 (implementation) depends on Tasks 1, 2, 3
- Task 5 (cleanup) is independent, can run parallel with Task 4
- Task 6 (full suite) depends on all above

**Recommended parallel groups:**
1. Group A: Tasks 1 + 2 (model + migration)
2. Group B: Task 5 (dead code removal) - independent
3. Sequential: Tasks 3 → 4 → 6 → 7
