# Eval Runbook Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a lightweight evaluation report (Eval Runbook) that auto-generates on eBay import, showing strategic fit scoring, FMV pricing, and acquisition recommendations.

**Architecture:** New `EvalRunbook` model linked 1:1 with Book. Backend API serves runbook data, frontend displays in modal with accordions. Price edits recalculate scoring without LLM calls.

**Tech Stack:** SQLAlchemy (model), Alembic (migration), FastAPI (API), Pydantic (schemas), Vue 3 + TypeScript (frontend), Tailwind CSS (styling)

---

## Phase 1: Backend Model & Migration

### Task 1.1: Create EvalRunbook Model

**Files:**
- Create: `backend/app/models/eval_runbook.py`
- Modify: `backend/app/models/__init__.py`

**Step 1: Create the model file**

```python
"""Eval Runbook model - lightweight evaluation report."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class EvalRunbook(Base, TimestampMixin):
    """Lightweight evaluation report for acquisition decisions."""

    __tablename__ = "eval_runbooks"

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"),
        unique=True,
    )

    # Scoring
    total_score: Mapped[int] = mapped_column(Integer, nullable=False)
    score_breakdown: Mapped[dict] = mapped_column(JSON, nullable=False)
    recommendation: Mapped[str] = mapped_column(String(20), nullable=False)  # PASS or ACQUIRE

    # Pricing
    original_asking_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    current_asking_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    discount_code: Mapped[str | None] = mapped_column(String(100))
    price_notes: Mapped[str | None] = mapped_column(Text)
    fmv_low: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    fmv_high: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    recommended_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    # FMV Comparables
    ebay_comparables: Mapped[list | None] = mapped_column(JSON)
    abebooks_comparables: Mapped[list | None] = mapped_column(JSON)

    # Content
    condition_grade: Mapped[str | None] = mapped_column(String(20))
    condition_positives: Mapped[list | None] = mapped_column(JSON)
    condition_negatives: Mapped[list | None] = mapped_column(JSON)
    critical_issues: Mapped[list | None] = mapped_column(JSON)
    analysis_narrative: Mapped[str | None] = mapped_column(Text)

    # Item identification (cached from book + listing)
    item_identification: Mapped[dict | None] = mapped_column(JSON)

    # Metadata
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    book = relationship("Book", back_populates="eval_runbook")


class EvalPriceHistory(Base):
    """Track price changes for eval runbooks."""

    __tablename__ = "eval_price_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    eval_runbook_id: Mapped[int] = mapped_column(
        ForeignKey("eval_runbooks.id", ondelete="CASCADE")
    )
    previous_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    new_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    discount_code: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    score_before: Mapped[int | None] = mapped_column(Integer)
    score_after: Mapped[int | None] = mapped_column(Integer)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

**Step 2: Update models __init__.py**

Add to `backend/app/models/__init__.py`:

```python
from app.models.eval_runbook import EvalPriceHistory, EvalRunbook
```

And add to `__all__`:

```python
__all__ = [
    # ... existing exports ...
    "EvalRunbook",
    "EvalPriceHistory",
]
```

**Step 3: Update Book model relationship**

Add to `backend/app/models/book.py` in the relationships section (after `analysis_jobs`):

```python
    eval_runbook = relationship(
        "EvalRunbook",
        back_populates="book",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
```

**Step 4: Run test to verify model loads**

Run: `poetry run --directory backend python -c "from app.models import EvalRunbook, EvalPriceHistory; print('Models loaded OK')"`
Expected: "Models loaded OK"

**Step 5: Commit**

```bash
git -C .worktrees/feat-eval-runbook add backend/app/models/eval_runbook.py backend/app/models/__init__.py backend/app/models/book.py
git -C .worktrees/feat-eval-runbook commit -m "feat(model): add EvalRunbook and EvalPriceHistory models"
```

---

### Task 1.2: Create Database Migration

**Files:**
- Create: `backend/alembic/versions/m5678901qrst_add_eval_runbook.py`

**Step 1: Create migration file**

```python
"""Add eval_runbooks and eval_price_history tables.

Revision ID: m5678901qrst
Revises: l4567890mnop
Create Date: 2025-12-15
"""

from alembic import op
import sqlalchemy as sa

revision = "m5678901qrst"
down_revision = "l4567890mnop"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eval_runbooks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False),
        sa.Column("score_breakdown", sa.JSON(), nullable=False),
        sa.Column("recommendation", sa.String(20), nullable=False),
        sa.Column("original_asking_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("current_asking_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("discount_code", sa.String(100), nullable=True),
        sa.Column("price_notes", sa.Text(), nullable=True),
        sa.Column("fmv_low", sa.Numeric(10, 2), nullable=True),
        sa.Column("fmv_high", sa.Numeric(10, 2), nullable=True),
        sa.Column("recommended_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("ebay_comparables", sa.JSON(), nullable=True),
        sa.Column("abebooks_comparables", sa.JSON(), nullable=True),
        sa.Column("condition_grade", sa.String(20), nullable=True),
        sa.Column("condition_positives", sa.JSON(), nullable=True),
        sa.Column("condition_negatives", sa.JSON(), nullable=True),
        sa.Column("critical_issues", sa.JSON(), nullable=True),
        sa.Column("analysis_narrative", sa.Text(), nullable=True),
        sa.Column("item_identification", sa.JSON(), nullable=True),
        sa.Column("generated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["book_id"], ["books.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("book_id"),
    )
    op.create_index("ix_eval_runbooks_book_id", "eval_runbooks", ["book_id"])

    op.create_table(
        "eval_price_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("eval_runbook_id", sa.Integer(), nullable=False),
        sa.Column("previous_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("new_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("discount_code", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("score_before", sa.Integer(), nullable=True),
        sa.Column("score_after", sa.Integer(), nullable=True),
        sa.Column("changed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["eval_runbook_id"], ["eval_runbooks.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("eval_price_history")
    op.drop_index("ix_eval_runbooks_book_id", table_name="eval_runbooks")
    op.drop_table("eval_runbooks")
```

**Step 2: Verify migration syntax**

Run: `poetry run --directory backend alembic check`
Expected: No errors

**Step 3: Commit**

```bash
git -C .worktrees/feat-eval-runbook add backend/alembic/versions/m5678901qrst_add_eval_runbook.py
git -C .worktrees/feat-eval-runbook commit -m "feat(migration): add eval_runbooks and eval_price_history tables"
```

---

## Phase 2: Backend Schemas & API

### Task 2.1: Create Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/eval_runbook.py`
- Modify: `backend/app/schemas/__init__.py`

**Step 1: Create schema file**

```python
"""Eval Runbook schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ScoreBreakdownItem(BaseModel):
    """Individual scoring criterion."""

    points: int
    notes: str


class FMVComparable(BaseModel):
    """A comparable listing for FMV calculation."""

    title: str
    price: Decimal
    condition: str | None = None
    days_ago: int | None = None  # For eBay sold


class EvalRunbookBase(BaseModel):
    """Base eval runbook schema."""

    total_score: int
    score_breakdown: dict[str, ScoreBreakdownItem]
    recommendation: str = Field(pattern="^(PASS|ACQUIRE)$")

    # Pricing
    original_asking_price: Decimal | None = None
    current_asking_price: Decimal | None = None
    discount_code: str | None = None
    price_notes: str | None = None
    fmv_low: Decimal | None = None
    fmv_high: Decimal | None = None
    recommended_price: Decimal | None = None

    # Comparables
    ebay_comparables: list[FMVComparable] | None = None
    abebooks_comparables: list[FMVComparable] | None = None

    # Content
    condition_grade: str | None = None
    condition_positives: list[str] | None = None
    condition_negatives: list[str] | None = None
    critical_issues: list[str] | None = None
    analysis_narrative: str | None = None
    item_identification: dict | None = None


class EvalRunbookResponse(EvalRunbookBase):
    """Eval runbook response schema."""

    id: int
    book_id: int
    generated_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EvalRunbookPriceUpdate(BaseModel):
    """Schema for updating eval runbook price."""

    new_price: Decimal
    discount_code: str | None = None
    notes: str | None = None


class EvalRunbookPriceUpdateResponse(BaseModel):
    """Response after price update with recalculated score."""

    previous_price: Decimal | None
    new_price: Decimal
    score_before: int
    score_after: int
    recommendation_before: str
    recommendation_after: str
    runbook: EvalRunbookResponse


class EvalPriceHistoryResponse(BaseModel):
    """Price history entry response."""

    id: int
    previous_price: Decimal | None
    new_price: Decimal | None
    discount_code: str | None
    notes: str | None
    score_before: int | None
    score_after: int | None
    changed_at: datetime

    class Config:
        from_attributes = True
```

**Step 2: Update schemas __init__.py**

Add to `backend/app/schemas/__init__.py`:

```python
from app.schemas.eval_runbook import (
    EvalPriceHistoryResponse,
    EvalRunbookBase,
    EvalRunbookPriceUpdate,
    EvalRunbookPriceUpdateResponse,
    EvalRunbookResponse,
    FMVComparable,
    ScoreBreakdownItem,
)
```

**Step 3: Verify schemas load**

Run: `poetry run --directory backend python -c "from app.schemas.eval_runbook import EvalRunbookResponse; print('Schemas loaded OK')"`
Expected: "Schemas loaded OK"

**Step 4: Commit**

```bash
git -C .worktrees/feat-eval-runbook add backend/app/schemas/eval_runbook.py backend/app/schemas/__init__.py
git -C .worktrees/feat-eval-runbook commit -m "feat(schemas): add EvalRunbook Pydantic schemas"
```

---

### Task 2.2: Create API Endpoints

**Files:**
- Create: `backend/app/api/v1/eval_runbook.py`
- Modify: `backend/app/api/v1/__init__.py`

**Step 1: Create API router**

```python
"""Eval Runbook API endpoints."""

import logging
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import Book, EvalPriceHistory, EvalRunbook, User
from app.schemas.eval_runbook import (
    EvalPriceHistoryResponse,
    EvalRunbookPriceUpdate,
    EvalRunbookPriceUpdateResponse,
    EvalRunbookResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/books/{book_id}/eval-runbook", tags=["eval-runbook"])

ACQUIRE_THRESHOLD = 80


def calculate_recommendation(score: int) -> str:
    """Determine recommendation based on score threshold."""
    return "ACQUIRE" if score >= ACQUIRE_THRESHOLD else "PASS"


def recalculate_score_for_price(
    runbook: EvalRunbook,
    new_price: Decimal,
) -> tuple[int, dict]:
    """Recalculate score when price changes.

    Returns (new_total_score, updated_breakdown).
    Only the 'Price vs FMV' criterion changes.
    """
    breakdown = dict(runbook.score_breakdown)
    fmv_mid = (runbook.fmv_low + runbook.fmv_high) / 2 if runbook.fmv_low and runbook.fmv_high else None

    # Calculate price points
    price_points = 0
    price_notes = "No FMV data"

    if fmv_mid and new_price:
        discount_pct = ((fmv_mid - new_price) / fmv_mid) * 100
        if discount_pct >= 30:
            price_points = 20
            price_notes = f"{discount_pct:.0f}% below FMV (excellent)"
        elif discount_pct >= 15:
            price_points = 10
            price_notes = f"{discount_pct:.0f}% below FMV (good)"
        elif discount_pct >= 0:
            price_points = 5
            price_notes = f"At or near FMV"
        else:
            price_points = 0
            price_notes = f"{abs(discount_pct):.0f}% above FMV"

    # Update breakdown
    breakdown["Price vs FMV"] = {"points": price_points, "notes": price_notes}

    # Recalculate total
    new_total = sum(item["points"] for item in breakdown.values())

    return new_total, breakdown


@router.get("", response_model=EvalRunbookResponse)
def get_eval_runbook(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get eval runbook for a book."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    runbook = db.query(EvalRunbook).filter(EvalRunbook.book_id == book_id).first()
    if not runbook:
        raise HTTPException(status_code=404, detail="Eval runbook not found")

    return runbook


@router.patch("/price", response_model=EvalRunbookPriceUpdateResponse)
def update_eval_runbook_price(
    book_id: int,
    price_update: EvalRunbookPriceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update asking price and recalculate score."""
    runbook = db.query(EvalRunbook).filter(EvalRunbook.book_id == book_id).first()
    if not runbook:
        raise HTTPException(status_code=404, detail="Eval runbook not found")

    # Store old values
    previous_price = runbook.current_asking_price
    score_before = runbook.total_score
    recommendation_before = runbook.recommendation

    # Recalculate score
    new_score, new_breakdown = recalculate_score_for_price(runbook, price_update.new_price)
    new_recommendation = calculate_recommendation(new_score)

    # Create price history record
    history = EvalPriceHistory(
        eval_runbook_id=runbook.id,
        previous_price=previous_price,
        new_price=price_update.new_price,
        discount_code=price_update.discount_code,
        notes=price_update.notes,
        score_before=score_before,
        score_after=new_score,
        changed_at=datetime.utcnow(),
    )
    db.add(history)

    # Update runbook
    runbook.current_asking_price = price_update.new_price
    runbook.discount_code = price_update.discount_code
    runbook.price_notes = price_update.notes
    runbook.total_score = new_score
    runbook.score_breakdown = new_breakdown
    runbook.recommendation = new_recommendation
    runbook.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(runbook)

    logger.info(f"Updated eval runbook price for book {book_id}: ${previous_price} -> ${price_update.new_price}, score {score_before} -> {new_score}")

    return EvalRunbookPriceUpdateResponse(
        previous_price=previous_price,
        new_price=price_update.new_price,
        score_before=score_before,
        score_after=new_score,
        recommendation_before=recommendation_before,
        recommendation_after=new_recommendation,
        runbook=runbook,
    )


@router.get("/history", response_model=list[EvalPriceHistoryResponse])
def get_price_history(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get price change history for eval runbook."""
    runbook = db.query(EvalRunbook).filter(EvalRunbook.book_id == book_id).first()
    if not runbook:
        raise HTTPException(status_code=404, detail="Eval runbook not found")

    history = (
        db.query(EvalPriceHistory)
        .filter(EvalPriceHistory.eval_runbook_id == runbook.id)
        .order_by(EvalPriceHistory.changed_at.desc())
        .all()
    )

    return history
```

**Step 2: Register router in __init__.py**

Add to `backend/app/api/v1/__init__.py`:

```python
from app.api.v1 import eval_runbook
```

And in the router includes section:

```python
api_router.include_router(eval_runbook.router)
```

**Step 3: Run API startup test**

Run: `poetry run --directory backend python -c "from app.main import app; print('API routes loaded OK')"`
Expected: "API routes loaded OK"

**Step 4: Commit**

```bash
git -C .worktrees/feat-eval-runbook add backend/app/api/v1/eval_runbook.py backend/app/api/v1/__init__.py
git -C .worktrees/feat-eval-runbook commit -m "feat(api): add eval runbook endpoints"
```

---

### Task 2.3: Add has_eval_runbook to Book Response

**Files:**
- Modify: `backend/app/schemas/book.py`

**Step 1: Add field to BookResponse**

In `backend/app/schemas/book.py`, add to `BookResponse` class:

```python
    has_eval_runbook: bool = False
```

**Step 2: Update book query to include flag**

In `backend/app/api/v1/books.py`, update the `_book_to_response` helper (or wherever books are serialized) to set:

```python
has_eval_runbook=book.eval_runbook is not None
```

**Step 3: Run tests**

Run: `poetry run --directory backend pytest tests/test_books.py -v -k "test_list" --tb=short`
Expected: Tests pass

**Step 4: Commit**

```bash
git -C .worktrees/feat-eval-runbook add backend/app/schemas/book.py backend/app/api/v1/books.py
git -C .worktrees/feat-eval-runbook commit -m "feat(api): add has_eval_runbook flag to book response"
```

---

## Phase 3: Frontend Store

### Task 3.1: Create Eval Runbook Store

**Files:**
- Create: `frontend/src/stores/evalRunbook.ts`

**Step 1: Create store file**

```typescript
import { defineStore } from "pinia";
import { ref } from "vue";
import { api } from "@/services/api";

export interface ScoreBreakdownItem {
  points: number;
  notes: string;
}

export interface FMVComparable {
  title: string;
  price: number;
  condition?: string;
  days_ago?: number;
}

export interface EvalRunbook {
  id: number;
  book_id: number;
  total_score: number;
  score_breakdown: Record<string, ScoreBreakdownItem>;
  recommendation: "PASS" | "ACQUIRE";
  original_asking_price?: number;
  current_asking_price?: number;
  discount_code?: string;
  price_notes?: string;
  fmv_low?: number;
  fmv_high?: number;
  recommended_price?: number;
  ebay_comparables?: FMVComparable[];
  abebooks_comparables?: FMVComparable[];
  condition_grade?: string;
  condition_positives?: string[];
  condition_negatives?: string[];
  critical_issues?: string[];
  analysis_narrative?: string;
  item_identification?: Record<string, string>;
  generated_at: string;
  created_at: string;
  updated_at: string;
}

export interface PriceUpdatePayload {
  new_price: number;
  discount_code?: string;
  notes?: string;
}

export interface PriceUpdateResponse {
  previous_price?: number;
  new_price: number;
  score_before: number;
  score_after: number;
  recommendation_before: string;
  recommendation_after: string;
  runbook: EvalRunbook;
}

export interface PriceHistoryEntry {
  id: number;
  previous_price?: number;
  new_price?: number;
  discount_code?: string;
  notes?: string;
  score_before?: number;
  score_after?: number;
  changed_at: string;
}

export const useEvalRunbookStore = defineStore("evalRunbook", () => {
  const currentRunbook = ref<EvalRunbook | null>(null);
  const priceHistory = ref<PriceHistoryEntry[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function fetchRunbook(bookId: number): Promise<EvalRunbook | null> {
    loading.value = true;
    error.value = null;
    try {
      const response = await api.get(`/books/${bookId}/eval-runbook`);
      currentRunbook.value = response.data;
      return response.data;
    } catch (e: any) {
      if (e.response?.status === 404) {
        currentRunbook.value = null;
        return null;
      }
      error.value = e.message || "Failed to fetch eval runbook";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function updatePrice(
    bookId: number,
    payload: PriceUpdatePayload
  ): Promise<PriceUpdateResponse> {
    loading.value = true;
    error.value = null;
    try {
      const response = await api.patch(`/books/${bookId}/eval-runbook/price`, payload);
      currentRunbook.value = response.data.runbook;
      return response.data;
    } catch (e: any) {
      error.value = e.message || "Failed to update price";
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function fetchPriceHistory(bookId: number): Promise<PriceHistoryEntry[]> {
    try {
      const response = await api.get(`/books/${bookId}/eval-runbook/history`);
      priceHistory.value = response.data;
      return response.data;
    } catch (e: any) {
      console.error("Failed to fetch price history:", e);
      return [];
    }
  }

  function clearRunbook() {
    currentRunbook.value = null;
    priceHistory.value = [];
    error.value = null;
  }

  return {
    currentRunbook,
    priceHistory,
    loading,
    error,
    fetchRunbook,
    updatePrice,
    fetchPriceHistory,
    clearRunbook,
  };
});
```

**Step 2: Verify TypeScript compiles**

Run: `npm --prefix frontend run type-check`
Expected: No errors

**Step 3: Commit**

```bash
git -C .worktrees/feat-eval-runbook add frontend/src/stores/evalRunbook.ts
git -C .worktrees/feat-eval-runbook commit -m "feat(store): add evalRunbook Pinia store"
```

---

## Phase 4: Frontend Modal Component

### Task 4.1: Create EvalRunbookModal Component

**Files:**
- Create: `frontend/src/components/books/EvalRunbookModal.vue`

**Step 1: Create modal component**

```vue
<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from "vue";
import { useEvalRunbookStore, type EvalRunbook, type PriceUpdatePayload } from "@/stores/evalRunbook";

const props = defineProps<{
  bookId: number;
  bookTitle: string;
}>();

const emit = defineEmits<{
  close: [];
}>();

const store = useEvalRunbookStore();
const loading = ref(true);
const runbook = ref<EvalRunbook | null>(null);

// Accordion state
const openSections = ref<Set<string>>(new Set(["identification"]));

// Price edit state
const showPriceEdit = ref(false);
const priceForm = ref<PriceUpdatePayload>({
  new_price: 0,
  discount_code: "",
  notes: "",
});
const priceUpdatePreview = ref<{ scoreDelta: number; newScore: number } | null>(null);
const updatingPrice = ref(false);

onMounted(async () => {
  document.body.style.overflow = "hidden";
  try {
    runbook.value = await store.fetchRunbook(props.bookId);
    if (runbook.value) {
      priceForm.value.new_price = runbook.value.current_asking_price || 0;
    }
  } finally {
    loading.value = false;
  }
});

onUnmounted(() => {
  document.body.style.overflow = "";
  store.clearRunbook();
});

const scoreColor = computed(() => {
  if (!runbook.value) return "bg-gray-200";
  const score = runbook.value.total_score;
  if (score >= 80) return "bg-green-500";
  if (score >= 60) return "bg-yellow-500";
  return "bg-red-500";
});

const scoreBadgeColor = computed(() => {
  if (!runbook.value) return "";
  return runbook.value.recommendation === "ACQUIRE"
    ? "bg-green-100 text-green-800"
    : "bg-yellow-100 text-yellow-800";
});

const fmvRange = computed(() => {
  if (!runbook.value?.fmv_low || !runbook.value?.fmv_high) return null;
  return `$${runbook.value.fmv_low.toFixed(0)}-$${runbook.value.fmv_high.toFixed(0)}`;
});

const priceDelta = computed(() => {
  if (!runbook.value?.current_asking_price || !runbook.value?.recommended_price) return null;
  return runbook.value.recommended_price - runbook.value.current_asking_price;
});

function toggleSection(section: string) {
  if (openSections.value.has(section)) {
    openSections.value.delete(section);
  } else {
    openSections.value.add(section);
  }
}

function isSectionOpen(section: string): boolean {
  return openSections.value.has(section);
}

function openPriceEdit() {
  if (runbook.value) {
    priceForm.value = {
      new_price: runbook.value.current_asking_price || 0,
      discount_code: runbook.value.discount_code || "",
      notes: "",
    };
  }
  showPriceEdit.value = true;
}

function closePriceEdit() {
  showPriceEdit.value = false;
  priceUpdatePreview.value = null;
}

// Calculate preview when price changes
watch(
  () => priceForm.value.new_price,
  (newPrice) => {
    if (!runbook.value || !newPrice) {
      priceUpdatePreview.value = null;
      return;
    }
    // Simple estimate - real calculation happens on server
    const fmvMid = runbook.value.fmv_low && runbook.value.fmv_high
      ? (runbook.value.fmv_low + runbook.value.fmv_high) / 2
      : null;

    if (fmvMid) {
      const currentPricePoints = runbook.value.score_breakdown["Price vs FMV"]?.points || 0;
      const discountPct = ((fmvMid - newPrice) / fmvMid) * 100;

      let newPricePoints = 0;
      if (discountPct >= 30) newPricePoints = 20;
      else if (discountPct >= 15) newPricePoints = 10;
      else if (discountPct >= 0) newPricePoints = 5;

      const scoreDelta = newPricePoints - currentPricePoints;
      priceUpdatePreview.value = {
        scoreDelta,
        newScore: runbook.value.total_score + scoreDelta,
      };
    }
  }
);

async function submitPriceUpdate() {
  updatingPrice.value = true;
  try {
    const result = await store.updatePrice(props.bookId, priceForm.value);
    runbook.value = result.runbook;
    closePriceEdit();
  } catch (e) {
    console.error("Failed to update price:", e);
  } finally {
    updatingPrice.value = false;
  }
}

function handleClose() {
  emit("close");
}

function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      @click.self="handleClose"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] flex flex-col">
        <!-- Header -->
        <div class="flex items-center justify-between p-4 border-b border-gray-200 shrink-0">
          <div>
            <h2 class="text-lg font-semibold text-gray-900">Eval Runbook</h2>
            <p class="text-sm text-gray-600 truncate">{{ bookTitle }}</p>
          </div>
          <button
            @click="handleClose"
            class="text-gray-500 hover:text-gray-700"
          >
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-y-auto p-4">
          <!-- Loading -->
          <div v-if="loading" class="flex items-center justify-center py-12">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>

          <!-- Not Found -->
          <div v-else-if="!runbook" class="text-center py-12">
            <p class="text-gray-500">No eval runbook generated for this book.</p>
          </div>

          <!-- Runbook Content -->
          <div v-else class="space-y-4">
            <!-- Score Summary -->
            <div class="bg-gray-50 rounded-lg p-4">
              <div class="text-sm font-medium text-gray-600 mb-2">Strategic Fit Score</div>
              <div class="relative h-4 bg-gray-200 rounded-full overflow-hidden mb-2">
                <div
                  :class="scoreColor"
                  class="absolute h-full transition-all duration-300"
                  :style="{ width: `${runbook.total_score}%` }"
                ></div>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-2xl font-bold">{{ runbook.total_score }} / 100</span>
                <span
                  :class="scoreBadgeColor"
                  class="px-3 py-1 rounded-full text-sm font-medium"
                >
                  {{ runbook.recommendation }}
                </span>
              </div>

              <!-- Pricing Row -->
              <div class="mt-4 grid grid-cols-4 gap-2 text-sm">
                <div>
                  <div class="text-gray-500">Asking</div>
                  <div class="font-medium flex items-center gap-1">
                    {{ formatCurrency(runbook.current_asking_price) }}
                    <button
                      @click="openPriceEdit"
                      class="text-blue-600 hover:text-blue-700"
                      title="Edit price"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                      </svg>
                    </button>
                  </div>
                </div>
                <div>
                  <div class="text-gray-500">Est. FMV</div>
                  <div class="font-medium">{{ fmvRange || "-" }}</div>
                </div>
                <div>
                  <div class="text-gray-500">Recommend</div>
                  <div class="font-medium">{{ formatCurrency(runbook.recommended_price) }}</div>
                </div>
                <div>
                  <div class="text-gray-500">Delta</div>
                  <div
                    class="font-medium"
                    :class="priceDelta && priceDelta < 0 ? 'text-red-600' : 'text-green-600'"
                  >
                    {{ priceDelta ? formatCurrency(priceDelta) : "-" }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Accordion Sections -->
            <!-- Item Identification -->
            <div class="border border-gray-200 rounded-lg">
              <button
                @click="toggleSection('identification')"
                class="w-full flex items-center justify-between p-3 text-left hover:bg-gray-50"
              >
                <span class="font-medium">Item Identification</span>
                <svg
                  class="w-5 h-5 transition-transform"
                  :class="{ 'rotate-180': isSectionOpen('identification') }"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              <div v-if="isSectionOpen('identification')" class="p-3 pt-0 border-t border-gray-200">
                <dl class="grid grid-cols-2 gap-2 text-sm">
                  <template v-for="(value, key) in runbook.item_identification" :key="key">
                    <dt class="text-gray-500">{{ key }}</dt>
                    <dd class="font-medium">{{ value }}</dd>
                  </template>
                </dl>
              </div>
            </div>

            <!-- Condition Assessment -->
            <div class="border border-gray-200 rounded-lg">
              <button
                @click="toggleSection('condition')"
                class="w-full flex items-center justify-between p-3 text-left hover:bg-gray-50"
              >
                <span class="font-medium">Condition Assessment</span>
                <span class="text-sm text-gray-500 mr-2">{{ runbook.condition_grade || "-" }}</span>
              </button>
              <div v-if="isSectionOpen('condition')" class="p-3 pt-0 border-t border-gray-200 text-sm">
                <div v-if="runbook.condition_positives?.length" class="mb-2">
                  <div class="font-medium text-green-700 mb-1">Positives</div>
                  <ul class="list-disc list-inside text-gray-600">
                    <li v-for="(item, i) in runbook.condition_positives" :key="i">{{ item }}</li>
                  </ul>
                </div>
                <div v-if="runbook.condition_negatives?.length">
                  <div class="font-medium text-red-700 mb-1">Negatives</div>
                  <ul class="list-disc list-inside text-gray-600">
                    <li v-for="(item, i) in runbook.condition_negatives" :key="i">{{ item }}</li>
                  </ul>
                </div>
              </div>
            </div>

            <!-- Strategic Scoring -->
            <div class="border border-gray-200 rounded-lg">
              <button
                @click="toggleSection('scoring')"
                class="w-full flex items-center justify-between p-3 text-left hover:bg-gray-50"
              >
                <span class="font-medium">Strategic Scoring</span>
                <span class="text-sm text-gray-500 mr-2">{{ runbook.total_score }} pts</span>
              </button>
              <div v-if="isSectionOpen('scoring')" class="p-3 pt-0 border-t border-gray-200">
                <table class="w-full text-sm">
                  <thead>
                    <tr class="text-left text-gray-500">
                      <th class="pb-2">Criterion</th>
                      <th class="pb-2 text-center">Points</th>
                      <th class="pb-2">Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(item, key) in runbook.score_breakdown" :key="key" class="border-t border-gray-100">
                      <td class="py-2">{{ key }}</td>
                      <td class="py-2 text-center" :class="item.points > 0 ? 'text-green-600 font-medium' : 'text-gray-400'">
                        {{ item.points > 0 ? `+${item.points}` : item.points }}
                      </td>
                      <td class="py-2 text-gray-600">{{ item.notes }}</td>
                    </tr>
                    <tr class="border-t-2 border-gray-300 font-medium">
                      <td class="py-2">TOTAL</td>
                      <td class="py-2 text-center">{{ runbook.total_score }}</td>
                      <td class="py-2 text-gray-600">
                        {{ runbook.total_score >= 80 ? "Meets threshold" : "Below 80pt threshold" }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- FMV Pricing -->
            <div class="border border-gray-200 rounded-lg">
              <button
                @click="toggleSection('fmv')"
                class="w-full flex items-center justify-between p-3 text-left hover:bg-gray-50"
              >
                <span class="font-medium">FMV Pricing</span>
                <span class="text-sm text-gray-500 mr-2">{{ fmvRange || "-" }}</span>
              </button>
              <div v-if="isSectionOpen('fmv')" class="p-3 pt-0 border-t border-gray-200 text-sm space-y-3">
                <!-- eBay Sold -->
                <div v-if="runbook.ebay_comparables?.length">
                  <div class="font-medium mb-1">eBay Sold (last 90 days)</div>
                  <div class="space-y-1">
                    <div
                      v-for="(comp, i) in runbook.ebay_comparables"
                      :key="i"
                      class="flex justify-between text-gray-600"
                    >
                      <span class="truncate mr-2">{{ comp.title }} - {{ comp.condition || "N/A" }}</span>
                      <span class="whitespace-nowrap">
                        {{ formatCurrency(comp.price) }}
                        <span v-if="comp.days_ago" class="text-gray-400 text-xs">{{ comp.days_ago }}d</span>
                      </span>
                    </div>
                  </div>
                </div>

                <!-- AbeBooks -->
                <div v-if="runbook.abebooks_comparables?.length">
                  <div class="font-medium mb-1">AbeBooks (current)</div>
                  <div class="space-y-1">
                    <div
                      v-for="(comp, i) in runbook.abebooks_comparables"
                      :key="i"
                      class="flex justify-between text-gray-600"
                    >
                      <span class="truncate mr-2">{{ comp.title }} - {{ comp.condition || "N/A" }}</span>
                      <span>{{ formatCurrency(comp.price) }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Critical Issues -->
            <div class="border border-gray-200 rounded-lg">
              <button
                @click="toggleSection('issues')"
                class="w-full flex items-center justify-between p-3 text-left hover:bg-gray-50"
              >
                <span class="font-medium">Critical Issues & Recommendation</span>
                <span v-if="runbook.critical_issues?.length" class="text-sm text-yellow-600 mr-2">
                  {{ runbook.critical_issues.length }} issues
                </span>
              </button>
              <div v-if="isSectionOpen('issues')" class="p-3 pt-0 border-t border-gray-200 text-sm">
                <ul v-if="runbook.critical_issues?.length" class="list-disc list-inside text-gray-600 space-y-1">
                  <li v-for="(issue, i) in runbook.critical_issues" :key="i">{{ issue }}</li>
                </ul>
                <p v-else class="text-gray-500">No critical issues identified.</p>
              </div>
            </div>

            <!-- Analysis Narrative -->
            <div class="border-t border-gray-200 pt-4">
              <div class="text-sm font-medium text-gray-600 mb-2 flex items-center gap-2">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Analysis Findings
              </div>
              <div class="text-sm text-gray-700 whitespace-pre-wrap bg-gray-50 rounded-lg p-3 max-h-64 overflow-y-auto">
                {{ runbook.analysis_narrative || "No analysis narrative available." }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Price Edit Modal -->
    <div
      v-if="showPriceEdit"
      class="fixed inset-0 z-[60] flex items-center justify-center bg-black/50"
      @click.self="closePriceEdit"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div class="flex items-center justify-between p-4 border-b border-gray-200">
          <h3 class="text-lg font-semibold">Update Asking Price</h3>
          <button @click="closePriceEdit" class="text-gray-500 hover:text-gray-700">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form @submit.prevent="submitPriceUpdate" class="p-4 space-y-4">
          <div>
            <div class="text-sm text-gray-500 mb-2">
              Original Listing Price: {{ formatCurrency(runbook?.original_asking_price) }}
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">New Price *</label>
            <div class="relative">
              <span class="absolute left-3 top-2 text-gray-500">$</span>
              <input
                v-model.number="priceForm.new_price"
                type="number"
                step="0.01"
                min="0"
                class="w-full pl-7 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Discount Code</label>
            <input
              v-model="priceForm.discount_code"
              type="text"
              placeholder="e.g., SAVE20"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Notes</label>
            <textarea
              v-model="priceForm.notes"
              rows="2"
              placeholder="e.g., Seller accepted offer"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            ></textarea>
          </div>

          <!-- Score Impact Preview -->
          <div v-if="priceUpdatePreview" class="bg-gray-50 rounded-lg p-3 text-sm">
            <div class="font-medium mb-1">Score Impact Preview</div>
            <div>
              Current: {{ runbook?.total_score }} pts →
              New: {{ priceUpdatePreview.newScore }} pts
              <span :class="priceUpdatePreview.scoreDelta >= 0 ? 'text-green-600' : 'text-red-600'">
                ({{ priceUpdatePreview.scoreDelta >= 0 ? "+" : "" }}{{ priceUpdatePreview.scoreDelta }})
              </span>
            </div>
            <div class="text-gray-500">
              Status: {{ runbook?.recommendation }} →
              {{ priceUpdatePreview.newScore >= 80 ? "ACQUIRE" : "Still PASS" }}
              <span v-if="priceUpdatePreview.newScore < 80">
                (need {{ formatCurrency(runbook?.recommended_price) }} for ACQUIRE)
              </span>
            </div>
          </div>

          <div class="flex gap-3 pt-2">
            <button
              type="button"
              @click="closePriceEdit"
              class="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="updatingPrice"
              class="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {{ updatingPrice ? "Saving..." : "Save & Recalculate" }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>
```

**Step 2: Run TypeScript check**

Run: `npm --prefix frontend run type-check`
Expected: No errors

**Step 3: Commit**

```bash
git -C .worktrees/feat-eval-runbook add frontend/src/components/books/EvalRunbookModal.vue
git -C .worktrees/feat-eval-runbook commit -m "feat(ui): add EvalRunbookModal component"
```

---

## Phase 5: Frontend Integration

### Task 5.1: Add Eval Runbook Button to BookDetailView

**Files:**
- Modify: `frontend/src/views/BookDetailView.vue`

**Step 1: Import modal and store**

Add imports at top of `<script setup>`:

```typescript
import EvalRunbookModal from "@/components/books/EvalRunbookModal.vue";

// Add state variable in the component
const evalRunbookVisible = ref(false);
```

**Step 2: Add button in template**

Find the analysis button section and add alongside it:

```vue
<!-- Analysis Buttons -->
<div class="flex gap-2 mt-4">
  <!-- Eval Runbook Button -->
  <button
    v-if="booksStore.currentBook?.has_eval_runbook"
    @click="evalRunbookVisible = true"
    class="flex items-center gap-2 px-3 py-2 text-sm bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100"
  >
    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
    Eval Runbook
    <span class="text-xs bg-blue-200 px-1.5 py-0.5 rounded">
      {{ booksStore.currentBook?.eval_score || "-" }}
    </span>
  </button>

  <!-- Napoleon Analysis Button (existing) -->
  <button
    v-if="hasAnalysis"
    @click="analysisVisible = true"
    class="flex items-center gap-2 px-3 py-2 text-sm bg-purple-50 text-purple-700 rounded-lg hover:bg-purple-100"
  >
    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
    </svg>
    Napoleon Analysis
  </button>
</div>
```

**Step 3: Add modal component**

At the bottom of the template, add:

```vue
<!-- Eval Runbook Modal -->
<EvalRunbookModal
  v-if="evalRunbookVisible && booksStore.currentBook"
  :book-id="booksStore.currentBook.id"
  :book-title="booksStore.currentBook.title"
  @close="evalRunbookVisible = false"
/>
```

**Step 4: Run dev server and verify**

Run: `npm --prefix frontend run dev`
Expected: Button appears on book detail page (when has_eval_runbook is true)

**Step 5: Commit**

```bash
git -C .worktrees/feat-eval-runbook add frontend/src/views/BookDetailView.vue
git -C .worktrees/feat-eval-runbook commit -m "feat(ui): add Eval Runbook button to BookDetailView"
```

---

## Phase 6: Backend Tests

### Task 6.1: Add API Tests

**Files:**
- Create: `backend/tests/test_eval_runbook.py`

**Step 1: Write test file**

```python
"""Tests for eval runbook API endpoints."""

from decimal import Decimal
from unittest.mock import patch

import pytest

from app.models import Book, EvalRunbook


class TestGetEvalRunbook:
    """Tests for GET /books/{id}/eval-runbook."""

    def test_returns_runbook_when_exists(self, client, db, auth_headers):
        """Test successful retrieval of eval runbook."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        runbook = EvalRunbook(
            book_id=book.id,
            total_score=65,
            score_breakdown={"Tier 1 Publisher": {"points": 0, "notes": "Not Tier 1"}},
            recommendation="PASS",
            original_asking_price=Decimal("275.00"),
            current_asking_price=Decimal("275.00"),
            fmv_low=Decimal("180.00"),
            fmv_high=Decimal("220.00"),
        )
        db.add(runbook)
        db.commit()

        response = client.get(f"/api/v1/books/{book.id}/eval-runbook", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_score"] == 65
        assert data["recommendation"] == "PASS"

    def test_returns_404_when_not_found(self, client, db, auth_headers):
        """Test 404 when runbook doesn't exist."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        response = client.get(f"/api/v1/books/{book.id}/eval-runbook", headers=auth_headers)

        assert response.status_code == 404

    def test_returns_404_for_nonexistent_book(self, client, auth_headers):
        """Test 404 when book doesn't exist."""
        response = client.get("/api/v1/books/99999/eval-runbook", headers=auth_headers)

        assert response.status_code == 404


class TestUpdatePrice:
    """Tests for PATCH /books/{id}/eval-runbook/price."""

    def test_updates_price_and_recalculates_score(self, client, db, auth_headers):
        """Test price update triggers score recalculation."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        runbook = EvalRunbook(
            book_id=book.id,
            total_score=60,
            score_breakdown={
                "Tier 1 Publisher": {"points": 0, "notes": "Not Tier 1"},
                "Victorian Era": {"points": 30, "notes": "1854"},
                "Complete Set": {"points": 20, "notes": "Single volume"},
                "Condition": {"points": 10, "notes": "Good+"},
                "Premium Binding": {"points": 0, "notes": "No binder"},
                "Price vs FMV": {"points": 0, "notes": "Above market"},
            },
            recommendation="PASS",
            original_asking_price=Decimal("275.00"),
            current_asking_price=Decimal("275.00"),
            fmv_low=Decimal("180.00"),
            fmv_high=Decimal("220.00"),
        )
        db.add(runbook)
        db.commit()

        response = client.patch(
            f"/api/v1/books/{book.id}/eval-runbook/price",
            json={"new_price": 160.00, "discount_code": "SAVE20", "notes": "Negotiated"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["previous_price"] == 275.00
        assert data["new_price"] == 160.00
        assert data["score_before"] == 60
        assert data["score_after"] > 60  # Should increase with better price
        assert data["runbook"]["discount_code"] == "SAVE20"

    def test_creates_price_history_record(self, client, db, auth_headers):
        """Test price update creates history record."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        runbook = EvalRunbook(
            book_id=book.id,
            total_score=60,
            score_breakdown={"Price vs FMV": {"points": 0, "notes": "Above market"}},
            recommendation="PASS",
            current_asking_price=Decimal("275.00"),
            fmv_low=Decimal("180.00"),
            fmv_high=Decimal("220.00"),
        )
        db.add(runbook)
        db.commit()

        client.patch(
            f"/api/v1/books/{book.id}/eval-runbook/price",
            json={"new_price": 200.00},
            headers=auth_headers,
        )

        # Check history
        response = client.get(f"/api/v1/books/{book.id}/eval-runbook/history", headers=auth_headers)
        assert response.status_code == 200
        history = response.json()
        assert len(history) == 1
        assert history[0]["previous_price"] == 275.00
        assert history[0]["new_price"] == 200.00
```

**Step 2: Run tests**

Run: `poetry run --directory backend pytest tests/test_eval_runbook.py -v`
Expected: All tests pass

**Step 3: Commit**

```bash
git -C .worktrees/feat-eval-runbook add backend/tests/test_eval_runbook.py
git -C .worktrees/feat-eval-runbook commit -m "test: add eval runbook API tests"
```

---

## Phase 7: Generation Service (Placeholder)

### Task 7.1: Create Eval Generation Service Stub

**Files:**
- Create: `backend/app/services/eval_generation.py`

**Step 1: Create service stub**

```python
"""Eval Runbook generation service.

This service generates the lightweight evaluation report based on:
1. Book metadata from eBay listing
2. Images analysis via Claude
3. FMV lookup from eBay sold + AbeBooks

TODO: Implement FMV lookup integration
TODO: Implement Claude evaluation prompt
"""

import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Book, EvalRunbook

logger = logging.getLogger(__name__)

ACQUIRE_THRESHOLD = 80


def generate_eval_runbook(
    book: Book,
    listing_data: dict,
    db: Session,
) -> EvalRunbook:
    """Generate eval runbook for a book.

    Args:
        book: Book model instance
        listing_data: Raw data from eBay listing import
        db: Database session

    Returns:
        Created EvalRunbook instance

    Note: This is a placeholder. Full implementation will include:
    - FMV lookup from eBay/AbeBooks
    - Claude-based condition assessment
    - Strategic scoring calculation
    """
    logger.info(f"Generating eval runbook for book {book.id}: {book.title}")

    # Placeholder scoring - will be replaced with actual logic
    score_breakdown = {
        "Tier 1 Publisher": {"points": 0, "notes": "TBD"},
        "Victorian Era": {"points": 0, "notes": "TBD"},
        "Complete Set": {"points": 0, "notes": "TBD"},
        "Condition": {"points": 0, "notes": "TBD"},
        "Premium Binding": {"points": 0, "notes": "TBD"},
        "Price vs FMV": {"points": 0, "notes": "TBD"},
    }

    total_score = sum(item["points"] for item in score_breakdown.values())
    recommendation = "ACQUIRE" if total_score >= ACQUIRE_THRESHOLD else "PASS"

    asking_price = listing_data.get("price")

    runbook = EvalRunbook(
        book_id=book.id,
        total_score=total_score,
        score_breakdown=score_breakdown,
        recommendation=recommendation,
        original_asking_price=Decimal(str(asking_price)) if asking_price else None,
        current_asking_price=Decimal(str(asking_price)) if asking_price else None,
        item_identification={
            "Title": book.title,
            "Author": listing_data.get("author", "Unknown"),
            "Publisher": listing_data.get("publisher", "Unknown"),
        },
        analysis_narrative="Evaluation pending. Full analysis will be generated after FMV lookup.",
    )

    db.add(runbook)
    db.commit()
    db.refresh(runbook)

    logger.info(f"Created eval runbook {runbook.id} for book {book.id}, score={total_score}")

    return runbook
```

**Step 2: Commit**

```bash
git -C .worktrees/feat-eval-runbook add backend/app/services/eval_generation.py
git -C .worktrees/feat-eval-runbook commit -m "feat(service): add eval generation service stub"
```

---

## Final Steps

### Task F.1: Run Full Test Suite

Run: `poetry run --directory backend pytest -v --tb=short`
Expected: All tests pass

Run: `npm --prefix frontend run test`
Expected: All tests pass

### Task F.2: Run Linters

Run: `poetry run --directory backend ruff check .`
Run: `poetry run --directory backend ruff format --check .`
Run: `npm --prefix frontend run lint`
Run: `npm --prefix frontend run type-check`
Expected: No errors

### Task F.3: Create PR to Staging

```bash
git -C .worktrees/feat-eval-runbook push -u origin feat/eval-runbook
gh pr create --base staging --head feat/eval-runbook --title "feat: Add Eval Runbook feature (#335)" --body "## Summary
- Add EvalRunbook model and database migration
- Add API endpoints for runbook retrieval and price updates
- Add frontend modal with accordion sections
- Add price edit with score recalculation preview
- Add eval runbook button to book detail page

## Design
See docs/plans/2025-12-15-eval-runbook-design.md

## Test Plan
- [ ] Backend tests pass
- [ ] Frontend tests pass
- [ ] Manual test: View eval runbook modal
- [ ] Manual test: Edit price and see score update

Closes #335"
```

---

**Plan complete and saved to `docs/plans/2025-12-15-eval-runbook-implementation.md`.** Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session in worktree, batch execution with checkpoints

Which approach?
