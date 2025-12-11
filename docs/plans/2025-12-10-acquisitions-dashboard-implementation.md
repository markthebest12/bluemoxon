# Acquisitions Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an in-app acquisitions dashboard that replaces the manual file-based workflow with a three-column Kanban (EVALUATING → IN_TRANSIT → ON_HAND).

**Architecture:** FastAPI backend with new status values, scoring calculation, and Bedrock integration. Vue 3 frontend with Pinia stores and new admin route. TDD approach with pytest (backend) and vitest (frontend).

**Tech Stack:** Python 3.14 / FastAPI / SQLAlchemy / Alembic / PostgreSQL, Vue 3 / TypeScript / Pinia / Tailwind CSS, AWS Bedrock (Claude 3 Sonnet)

**Worktree:** `/Users/mark/projects/bluemoxon/.worktrees/acquisitions-dashboard`
**Branch:** `feature/acquisitions-dashboard`

---

## Phase 1: Database Schema Changes

### Task 1.1: Add New Status Values to Book Model

**Files:**
- Modify: `backend/app/models/book.py`

**Step 1: Update status field docstring**

Add documentation for all valid status values:

```python
# In Book class, update status field comment:
# Status: EVALUATING, IN_TRANSIT, ON_HAND, SOLD, REMOVED, CANCELED
status: Mapped[str] = mapped_column(String(20), default="ON_HAND")
```

**Step 2: Run existing tests to confirm no regression**

Run: `cd backend && .venv/bin/python -m pytest tests -q --tb=short`
Expected: All 84 tests pass

**Step 3: Commit**

```bash
git add backend/app/models/book.py
git commit -m "docs: Document valid status values including EVALUATING and CANCELED"
```

---

### Task 1.2: Add New Columns to Book Model

**Files:**
- Modify: `backend/app/models/book.py`

**Step 1: Add imports for JSONB**

```python
# At top of file, add to postgresql imports:
from sqlalchemy.dialects.postgresql import JSONB
```

**Step 2: Add new columns after existing `status` field (around line 67)**

```python
    # Source tracking
    source_url: Mapped[str | None] = mapped_column(String(500))
    source_item_id: Mapped[str | None] = mapped_column(String(100))

    # Delivery tracking
    estimated_delivery: Mapped[date | None] = mapped_column(Date)

    # Acquisition scoring (captured at purchase time)
    scoring_snapshot: Mapped[dict | None] = mapped_column(JSONB)
```

**Step 3: Add index for source_item_id lookups**

```python
# In __table_args__ tuple, add:
Index("books_source_item_id_idx", "source_item_id"),
```

**Step 4: Run tests**

Run: `cd backend && .venv/bin/python -m pytest tests -q --tb=short`
Expected: All tests pass (SQLite will use TEXT for JSONB)

**Step 5: Commit**

```bash
git add backend/app/models/book.py
git commit -m "feat(models): Add source tracking and scoring columns to Book"
```

---

### Task 1.3: Create Alembic Migration

**Files:**
- Create: `backend/alembic/versions/xxxx_add_acquisition_columns.py`

**Step 1: Generate migration**

```bash
cd backend
.venv/bin/alembic revision -m "add_acquisition_columns"
```

**Step 2: Edit the generated migration file**

```python
"""add_acquisition_columns

Revision ID: [generated]
Revises: d4e5f6789abc
Create Date: [generated]

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '[generated]'
down_revision: Union[str, None] = 'd4e5f6789abc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns
    op.add_column('books', sa.Column('source_url', sa.String(500), nullable=True))
    op.add_column('books', sa.Column('source_item_id', sa.String(100), nullable=True))
    op.add_column('books', sa.Column('estimated_delivery', sa.Date(), nullable=True))
    op.add_column('books', sa.Column('scoring_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # Add index for source_item_id lookups
    op.create_index('books_source_item_id_idx', 'books', ['source_item_id'])


def downgrade() -> None:
    op.drop_index('books_source_item_id_idx', table_name='books')
    op.drop_column('books', 'scoring_snapshot')
    op.drop_column('books', 'estimated_delivery')
    op.drop_column('books', 'source_item_id')
    op.drop_column('books', 'source_url')
```

**Step 3: Commit migration**

```bash
git add backend/alembic/versions/
git commit -m "feat(db): Add migration for acquisition tracking columns"
```

---

### Task 1.4: Update Book Schemas

**Files:**
- Modify: `backend/app/schemas/book.py`

**Step 1: Add new fields to BookBase (around line 35)**

```python
    # Source tracking
    source_url: str | None = None
    source_item_id: str | None = None

    # Delivery tracking
    estimated_delivery: date | None = None
```

**Step 2: Add scoring_snapshot to BookResponse (after line 119)**

```python
    scoring_snapshot: dict | None = None
```

**Step 3: Add new fields to BookUpdate (around line 72)**

```python
    source_url: str | None = None
    source_item_id: str | None = None
    estimated_delivery: date | None = None
```

**Step 4: Run tests**

Run: `cd backend && .venv/bin/python -m pytest tests -q --tb=short`
Expected: All tests pass

**Step 5: Commit**

```bash
git add backend/app/schemas/book.py
git commit -m "feat(schemas): Add acquisition tracking fields to book schemas"
```

---

## Phase 2: Acquisition API Endpoint

### Task 2.1: Create Acquisition Schema

**Files:**
- Modify: `backend/app/schemas/book.py`

**Step 1: Add AcquireRequest schema (at end of file)**

```python
class AcquireRequest(BaseModel):
    """Request body for acquiring a book (EVALUATING -> IN_TRANSIT)."""

    purchase_price: Decimal
    purchase_date: date
    order_number: str
    place_of_purchase: str
    estimated_delivery: date | None = None


class ScoringSnapshot(BaseModel):
    """Scoring data captured at acquisition time."""

    captured_at: datetime
    purchase_price: Decimal
    fmv_at_purchase: dict  # {"low": x, "mid": y, "high": z}
    discount_pct: Decimal
    investment_grade: Decimal
    strategic_fit: dict  # {"score": x, "max": y, "criteria": [...]}
    collection_position: dict  # {"items_before": x, "volumes_before": y}
```

**Step 2: Run tests**

Run: `cd backend && .venv/bin/python -m pytest tests -q --tb=short`
Expected: All tests pass

**Step 3: Commit**

```bash
git add backend/app/schemas/book.py
git commit -m "feat(schemas): Add AcquireRequest and ScoringSnapshot schemas"
```

---

### Task 2.2: Write Failing Test for Acquire Endpoint

**Files:**
- Create: `backend/tests/api/v1/test_acquire.py`

**Step 1: Create test file**

```python
"""Tests for book acquisition endpoint."""

import pytest
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app
from app.models import Book


@pytest.fixture
def evaluating_book(db_session):
    """Create a book in EVALUATING status for testing."""
    book = Book(
        title="Test Book for Acquisition",
        status="EVALUATING",
        inventory_type="PRIMARY",
        value_low=Decimal("400.00"),
        value_mid=Decimal("475.00"),
        value_high=Decimal("550.00"),
        volumes=1,
    )
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)
    return book


class TestAcquireEndpoint:
    """Tests for PATCH /books/{id}/acquire endpoint."""

    def test_acquire_changes_status_to_in_transit(
        self, client: TestClient, evaluating_book: Book, api_key_header: dict
    ):
        """Acquiring a book should change status from EVALUATING to IN_TRANSIT."""
        response = client.patch(
            f"/api/v1/books/{evaluating_book.id}/acquire",
            json={
                "purchase_price": 164.14,
                "purchase_date": "2025-12-10",
                "order_number": "19-13940-40744",
                "place_of_purchase": "eBay",
            },
            headers=api_key_header,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "IN_TRANSIT"
        assert float(data["purchase_price"]) == 164.14
        assert data["purchase_source"] == "eBay"

    def test_acquire_calculates_discount_percentage(
        self, client: TestClient, evaluating_book: Book, api_key_header: dict
    ):
        """Acquire should calculate discount_pct based on purchase_price vs value_mid."""
        response = client.patch(
            f"/api/v1/books/{evaluating_book.id}/acquire",
            json={
                "purchase_price": 164.14,
                "purchase_date": "2025-12-10",
                "order_number": "test-order",
                "place_of_purchase": "eBay",
            },
            headers=api_key_header,
        )

        assert response.status_code == 200
        data = response.json()
        # discount = (475 - 164.14) / 475 * 100 = 65.44%
        assert float(data["discount_pct"]) == pytest.approx(65.44, rel=0.01)

    def test_acquire_creates_scoring_snapshot(
        self, client: TestClient, evaluating_book: Book, api_key_header: dict
    ):
        """Acquire should create a scoring_snapshot with acquisition-time data."""
        response = client.patch(
            f"/api/v1/books/{evaluating_book.id}/acquire",
            json={
                "purchase_price": 164.14,
                "purchase_date": "2025-12-10",
                "order_number": "test-order",
                "place_of_purchase": "eBay",
            },
            headers=api_key_header,
        )

        assert response.status_code == 200
        data = response.json()
        snapshot = data["scoring_snapshot"]
        assert snapshot is not None
        assert "captured_at" in snapshot
        assert float(snapshot["purchase_price"]) == 164.14
        assert snapshot["fmv_at_purchase"]["mid"] == 475.0

    def test_acquire_rejects_non_evaluating_book(
        self, client: TestClient, db_session, api_key_header: dict
    ):
        """Cannot acquire a book that is not in EVALUATING status."""
        book = Book(
            title="Already Acquired Book",
            status="ON_HAND",
            inventory_type="PRIMARY",
            volumes=1,
        )
        db_session.add(book)
        db_session.commit()

        response = client.patch(
            f"/api/v1/books/{book.id}/acquire",
            json={
                "purchase_price": 100.00,
                "purchase_date": "2025-12-10",
                "order_number": "test",
                "place_of_purchase": "eBay",
            },
            headers=api_key_header,
        )

        assert response.status_code == 400
        assert "EVALUATING" in response.json()["detail"]

    def test_acquire_requires_editor_role(
        self, client: TestClient, evaluating_book: Book
    ):
        """Acquire endpoint requires editor or admin role."""
        response = client.patch(
            f"/api/v1/books/{evaluating_book.id}/acquire",
            json={
                "purchase_price": 100.00,
                "purchase_date": "2025-12-10",
                "order_number": "test",
                "place_of_purchase": "eBay",
            },
        )

        # Should fail without auth
        assert response.status_code in [401, 403]
```

**Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/api/v1/test_acquire.py -v`
Expected: FAIL - endpoint doesn't exist yet (404)

**Step 3: Commit failing test**

```bash
git add backend/tests/api/v1/test_acquire.py
git commit -m "test: Add failing tests for acquire endpoint"
```

---

### Task 2.3: Implement Acquire Endpoint

**Files:**
- Modify: `backend/app/api/v1/books.py`

**Step 1: Add import for AcquireRequest schema**

```python
from app.schemas.book import (
    AcquireRequest,
    BookCreate,
    BookListResponse,
    BookResponse,
    BookUpdate,
)
```

**Step 2: Add acquire endpoint (after existing endpoints, around line 300)**

```python
@router.patch("/{book_id}/acquire", response_model=BookResponse)
def acquire_book(
    book_id: int,
    acquire_data: AcquireRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_editor),
):
    """
    Acquire a book - transition from EVALUATING to IN_TRANSIT.

    Calculates discount percentage and creates scoring snapshot.
    """
    from datetime import datetime
    from decimal import Decimal

    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.status != "EVALUATING":
        raise HTTPException(
            status_code=400,
            detail=f"Book must be in EVALUATING status to acquire (current: {book.status})"
        )

    # Update acquisition fields
    book.purchase_price = acquire_data.purchase_price
    book.purchase_date = acquire_data.purchase_date
    book.purchase_source = acquire_data.place_of_purchase
    book.status = "IN_TRANSIT"

    if acquire_data.estimated_delivery:
        book.estimated_delivery = acquire_data.estimated_delivery

    # Store order number in notes (or create order_number field later)
    if book.notes:
        book.notes = f"Order: {acquire_data.order_number}\n{book.notes}"
    else:
        book.notes = f"Order: {acquire_data.order_number}"

    # Calculate discount percentage
    if book.value_mid and acquire_data.purchase_price:
        discount = (float(book.value_mid) - float(acquire_data.purchase_price)) / float(book.value_mid) * 100
        book.discount_pct = Decimal(str(round(discount, 2)))

    # Get collection stats for scoring
    from sqlalchemy import func

    collection_stats = db.query(
        func.count(Book.id).label("items"),
        func.sum(Book.volumes).label("volumes"),
    ).filter(
        Book.inventory_type == "PRIMARY",
        Book.status == "ON_HAND",
    ).first()

    # Create scoring snapshot
    book.scoring_snapshot = {
        "captured_at": datetime.utcnow().isoformat(),
        "purchase_price": float(acquire_data.purchase_price),
        "fmv_at_purchase": {
            "low": float(book.value_low) if book.value_low else None,
            "mid": float(book.value_mid) if book.value_mid else None,
            "high": float(book.value_high) if book.value_high else None,
        },
        "discount_pct": float(book.discount_pct) if book.discount_pct else 0,
        "collection_position": {
            "items_before": collection_stats.items if collection_stats else 0,
            "volumes_before": int(collection_stats.volumes) if collection_stats and collection_stats.volumes else 0,
        },
    }

    db.commit()
    db.refresh(book)

    # Build response with image info
    base_url = get_api_base_url()
    response = BookResponse.model_validate(book).model_dump()
    response["has_analysis"] = book.analysis is not None
    response["image_count"] = len(book.images) if book.images else 0

    if book.images:
        primary = next((img for img in book.images if img.is_primary), book.images[0])
        if is_production():
            response["primary_image_url"] = get_cloudfront_url(primary.s3_key, "thumb")
        else:
            response["primary_image_url"] = f"{base_url}/api/v1/books/{book.id}/images/{primary.id}/thumbnail"

    return response
```

**Step 3: Run tests**

Run: `cd backend && .venv/bin/python -m pytest tests/api/v1/test_acquire.py -v`
Expected: All tests pass

**Step 4: Run full test suite**

Run: `cd backend && .venv/bin/python -m pytest tests -q --tb=short`
Expected: All tests pass

**Step 5: Commit**

```bash
git add backend/app/api/v1/books.py
git commit -m "feat(api): Add acquire endpoint for EVALUATING -> IN_TRANSIT transition"
```

---

## Phase 3: Frontend - Acquisitions Dashboard Layout

### Task 3.1: Create Acquisitions Store

**Files:**
- Create: `frontend/src/stores/acquisitions.ts`

**Step 1: Create the store**

```typescript
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "@/services/api";

export interface AcquisitionBook {
  id: number;
  title: string;
  author?: { id: number; name: string };
  publisher?: { id: number; name: string; tier?: string };
  binder?: { id: number; name: string };
  status: string;
  value_low?: number;
  value_mid?: number;
  value_high?: number;
  purchase_price?: number;
  purchase_date?: string;
  discount_pct?: number;
  estimated_delivery?: string;
  scoring_snapshot?: Record<string, unknown>;
  primary_image_url?: string;
}

export interface AcquirePayload {
  purchase_price: number;
  purchase_date: string;
  order_number: string;
  place_of_purchase: string;
  estimated_delivery?: string;
}

export const useAcquisitionsStore = defineStore("acquisitions", () => {
  const evaluating = ref<AcquisitionBook[]>([]);
  const inTransit = ref<AcquisitionBook[]>([]);
  const received = ref<AcquisitionBook[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const evaluatingCount = computed(() => evaluating.value.length);
  const inTransitCount = computed(() => inTransit.value.length);
  const receivedCount = computed(() => received.value.length);

  async function fetchAll() {
    loading.value = true;
    error.value = null;

    try {
      const [evalRes, transitRes, receivedRes] = await Promise.all([
        api.get("/books", { params: { status: "EVALUATING", inventory_type: "PRIMARY", per_page: 100 } }),
        api.get("/books", { params: { status: "IN_TRANSIT", inventory_type: "PRIMARY", per_page: 100 } }),
        api.get("/books", { params: { status: "ON_HAND", inventory_type: "PRIMARY", per_page: 50, sort_by: "purchase_date", sort_order: "desc" } }),
      ]);

      evaluating.value = evalRes.data.items;
      inTransit.value = transitRes.data.items;
      // Only show last 30 days of received
      const thirtyDaysAgo = new Date();
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
      received.value = receivedRes.data.items.filter((b: AcquisitionBook) => {
        if (!b.purchase_date) return false;
        return new Date(b.purchase_date) >= thirtyDaysAgo;
      });
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to load acquisitions";
    } finally {
      loading.value = false;
    }
  }

  async function acquireBook(bookId: number, payload: AcquirePayload) {
    const response = await api.patch(`/books/${bookId}/acquire`, payload);
    // Move from evaluating to inTransit
    evaluating.value = evaluating.value.filter((b) => b.id !== bookId);
    inTransit.value.unshift(response.data);
    return response.data;
  }

  async function markReceived(bookId: number) {
    const response = await api.patch(`/books/${bookId}/status`, null, {
      params: { status: "ON_HAND" },
    });
    // Move from inTransit to received
    inTransit.value = inTransit.value.filter((b) => b.id !== bookId);
    received.value.unshift(response.data);
    return response.data;
  }

  async function cancelOrder(bookId: number) {
    const response = await api.patch(`/books/${bookId}/status`, null, {
      params: { status: "CANCELED" },
    });
    inTransit.value = inTransit.value.filter((b) => b.id !== bookId);
    return response.data;
  }

  async function deleteEvaluating(bookId: number) {
    await api.delete(`/books/${bookId}`);
    evaluating.value = evaluating.value.filter((b) => b.id !== bookId);
  }

  return {
    evaluating,
    inTransit,
    received,
    loading,
    error,
    evaluatingCount,
    inTransitCount,
    receivedCount,
    fetchAll,
    acquireBook,
    markReceived,
    cancelOrder,
    deleteEvaluating,
  };
});
```

**Step 2: Commit**

```bash
git add frontend/src/stores/acquisitions.ts
git commit -m "feat(store): Add acquisitions store for dashboard state management"
```

---

### Task 3.2: Create Acquisitions Dashboard View

**Files:**
- Create: `frontend/src/views/AcquisitionsView.vue`

**Step 1: Create the view**

```vue
<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useAcquisitionsStore } from "@/stores/acquisitions";
import { useAuthStore } from "@/stores/auth";
import { storeToRefs } from "pinia";

const acquisitionsStore = useAcquisitionsStore();
const authStore = useAuthStore();
const { evaluating, inTransit, received, loading, error } = storeToRefs(acquisitionsStore);
const { isAdmin, isEditor } = storeToRefs(authStore);

const showAcquireModal = ref(false);
const selectedBookId = ref<number | null>(null);

onMounted(() => {
  acquisitionsStore.fetchAll();
});

function openAcquireModal(bookId: number) {
  selectedBookId.value = bookId;
  showAcquireModal.value = true;
}

function formatPrice(price?: number): string {
  if (!price) return "-";
  return `$${price.toFixed(2)}`;
}

function formatDiscount(discount?: number): string {
  if (!discount) return "-";
  return `${discount.toFixed(0)}%`;
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

async function handleMarkReceived(bookId: number) {
  await acquisitionsStore.markReceived(bookId);
}

async function handleDelete(bookId: number) {
  if (confirm("Delete this item from watchlist?")) {
    await acquisitionsStore.deleteEvaluating(bookId);
  }
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 p-6">
    <div class="max-w-7xl mx-auto">
      <!-- Header -->
      <div class="mb-6">
        <h1 class="text-2xl font-bold text-gray-900">Acquisitions</h1>
        <p class="text-gray-600">Track books from watchlist through delivery</p>
      </div>

      <!-- Error State -->
      <div v-if="error" class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
        <p class="text-red-700">{{ error }}</p>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="flex justify-center py-12">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>

      <!-- Kanban Board -->
      <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- EVALUATING Column -->
        <div class="bg-white rounded-lg shadow">
          <div class="p-4 border-b border-gray-200">
            <h2 class="font-semibold text-gray-900 flex items-center gap-2">
              <span class="w-3 h-3 bg-yellow-400 rounded-full"></span>
              Evaluating
              <span class="ml-auto text-sm text-gray-500">{{ evaluating.length }}</span>
            </h2>
          </div>
          <div class="p-4 space-y-3 max-h-[calc(100vh-280px)] overflow-y-auto">
            <div
              v-for="book in evaluating"
              :key="book.id"
              class="bg-gray-50 rounded-lg p-3 border border-gray-200 hover:border-blue-300 transition-colors"
            >
              <h3 class="font-medium text-gray-900 text-sm truncate">{{ book.title }}</h3>
              <p class="text-xs text-gray-600 truncate">{{ book.author?.name || "Unknown author" }}</p>
              <div class="mt-2 flex items-center justify-between text-xs">
                <span class="text-gray-500">FMV: {{ formatPrice(book.value_mid) }}</span>
              </div>
              <div class="mt-3 flex gap-2">
                <button
                  @click="openAcquireModal(book.id)"
                  class="flex-1 px-2 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700"
                >
                  Acquire
                </button>
                <button
                  @click="handleDelete(book.id)"
                  class="px-2 py-1 text-red-600 text-xs hover:bg-red-50 rounded"
                >
                  Delete
                </button>
              </div>
            </div>

            <!-- Add Item Button -->
            <router-link
              to="/books/new?status=EVALUATING"
              class="block w-full p-3 border-2 border-dashed border-gray-300 rounded-lg text-center text-sm text-gray-500 hover:border-blue-400 hover:text-blue-600"
            >
              + Add to Watchlist
            </router-link>
          </div>
        </div>

        <!-- IN_TRANSIT Column -->
        <div class="bg-white rounded-lg shadow">
          <div class="p-4 border-b border-gray-200">
            <h2 class="font-semibold text-gray-900 flex items-center gap-2">
              <span class="w-3 h-3 bg-blue-400 rounded-full"></span>
              In Transit
              <span class="ml-auto text-sm text-gray-500">{{ inTransit.length }}</span>
            </h2>
          </div>
          <div class="p-4 space-y-3 max-h-[calc(100vh-280px)] overflow-y-auto">
            <div
              v-for="book in inTransit"
              :key="book.id"
              class="bg-gray-50 rounded-lg p-3 border border-gray-200"
            >
              <h3 class="font-medium text-gray-900 text-sm truncate">{{ book.title }}</h3>
              <p class="text-xs text-gray-600 truncate">{{ book.author?.name || "Unknown author" }}</p>
              <div class="mt-2 grid grid-cols-2 gap-1 text-xs">
                <span class="text-gray-500">Paid: {{ formatPrice(book.purchase_price) }}</span>
                <span class="text-green-600 font-medium">{{ formatDiscount(book.discount_pct) }} off</span>
              </div>
              <div v-if="book.estimated_delivery" class="mt-1 text-xs text-gray-500">
                Due: {{ formatDate(book.estimated_delivery) }}
              </div>
              <div class="mt-3">
                <button
                  @click="handleMarkReceived(book.id)"
                  class="w-full px-2 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700"
                >
                  Mark Received
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- RECEIVED Column -->
        <div class="bg-white rounded-lg shadow">
          <div class="p-4 border-b border-gray-200">
            <h2 class="font-semibold text-gray-900 flex items-center gap-2">
              <span class="w-3 h-3 bg-green-400 rounded-full"></span>
              Received (30d)
              <span class="ml-auto text-sm text-gray-500">{{ received.length }}</span>
            </h2>
          </div>
          <div class="p-4 space-y-3 max-h-[calc(100vh-280px)] overflow-y-auto">
            <router-link
              v-for="book in received"
              :key="book.id"
              :to="`/books/${book.id}`"
              class="block bg-gray-50 rounded-lg p-3 border border-gray-200 hover:border-green-300 transition-colors"
            >
              <h3 class="font-medium text-gray-900 text-sm truncate">{{ book.title }}</h3>
              <p class="text-xs text-gray-600 truncate">{{ book.author?.name || "Unknown author" }}</p>
              <div class="mt-2 grid grid-cols-2 gap-1 text-xs">
                <span class="text-gray-500">Paid: {{ formatPrice(book.purchase_price) }}</span>
                <span class="text-green-600 font-medium">{{ formatDiscount(book.discount_pct) }} off</span>
              </div>
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
```

**Step 2: Commit**

```bash
git add frontend/src/views/AcquisitionsView.vue
git commit -m "feat(ui): Add acquisitions dashboard view with Kanban layout"
```

---

### Task 3.3: Add Route for Acquisitions Dashboard

**Files:**
- Modify: `frontend/src/router/index.ts`

**Step 1: Add route after admin route (around line 63)**

```typescript
    {
      path: "/admin/acquisitions",
      name: "acquisitions",
      component: () => import("@/views/AcquisitionsView.vue"),
      meta: { requiresAuth: true, requiresAdmin: true },
    },
```

**Step 2: Run frontend tests**

Run: `cd frontend && npm test`
Expected: All tests pass

**Step 3: Commit**

```bash
git add frontend/src/router/index.ts
git commit -m "feat(router): Add /admin/acquisitions route"
```

---

## Phase 4: Acquire Modal Component

### Task 4.1: Create Acquire Modal Component

**Files:**
- Create: `frontend/src/components/AcquireModal.vue`

**Step 1: Create the component**

```vue
<script setup lang="ts">
import { ref, computed } from "vue";
import { useAcquisitionsStore, type AcquirePayload } from "@/stores/acquisitions";

const props = defineProps<{
  bookId: number;
  bookTitle: string;
  valueMid?: number;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "acquired"): void;
}>();

const acquisitionsStore = useAcquisitionsStore();

const form = ref<AcquirePayload>({
  purchase_price: 0,
  purchase_date: new Date().toISOString().split("T")[0],
  order_number: "",
  place_of_purchase: "eBay",
  estimated_delivery: undefined,
});

const submitting = ref(false);
const errorMessage = ref<string | null>(null);

const estimatedDiscount = computed(() => {
  if (!props.valueMid || !form.value.purchase_price) return null;
  const discount = ((props.valueMid - form.value.purchase_price) / props.valueMid) * 100;
  return discount.toFixed(1);
});

async function handleSubmit() {
  if (!form.value.purchase_price || !form.value.order_number) {
    errorMessage.value = "Please fill in all required fields";
    return;
  }

  submitting.value = true;
  errorMessage.value = null;

  try {
    await acquisitionsStore.acquireBook(props.bookId, form.value);
    emit("acquired");
    emit("close");
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : "Failed to acquire book";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
      <div class="p-4 border-b border-gray-200">
        <h2 class="text-lg font-semibold text-gray-900">Acquire Book</h2>
        <p class="text-sm text-gray-600 truncate">{{ bookTitle }}</p>
      </div>

      <form @submit.prevent="handleSubmit" class="p-4 space-y-4">
        <div v-if="errorMessage" class="bg-red-50 text-red-700 p-3 rounded text-sm">
          {{ errorMessage }}
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Purchase Price *
          </label>
          <div class="relative">
            <span class="absolute left-3 top-2 text-gray-500">$</span>
            <input
              v-model.number="form.purchase_price"
              type="number"
              step="0.01"
              min="0"
              class="w-full pl-7 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>
          <p v-if="estimatedDiscount" class="mt-1 text-sm text-green-600">
            {{ estimatedDiscount }}% discount from FMV (${{ valueMid }})
          </p>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Purchase Date *
          </label>
          <input
            v-model="form.purchase_date"
            type="date"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            required
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Order Number *
          </label>
          <input
            v-model="form.order_number"
            type="text"
            placeholder="19-13940-40744"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            required
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Platform *
          </label>
          <select
            v-model="form.place_of_purchase"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="eBay">eBay</option>
            <option value="Etsy">Etsy</option>
            <option value="AbeBooks">AbeBooks</option>
            <option value="Other">Other</option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Estimated Delivery
          </label>
          <input
            v-model="form.estimated_delivery"
            type="date"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <div class="flex gap-3 pt-4">
          <button
            type="button"
            @click="emit('close')"
            class="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            :disabled="submitting"
            class="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {{ submitting ? "Processing..." : "Confirm Acquire" }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
```

**Step 2: Commit**

```bash
git add frontend/src/components/AcquireModal.vue
git commit -m "feat(ui): Add acquire modal component with order details form"
```

---

### Task 4.2: Wire Up Acquire Modal in Dashboard

**Files:**
- Modify: `frontend/src/views/AcquisitionsView.vue`

**Step 1: Import and use the modal component**

Add to script section:
```typescript
import AcquireModal from "@/components/AcquireModal.vue";

const selectedBook = computed(() => {
  if (!selectedBookId.value) return null;
  return evaluating.value.find((b) => b.id === selectedBookId.value);
});

function closeAcquireModal() {
  showAcquireModal.value = false;
  selectedBookId.value = null;
}
```

**Step 2: Add modal to template (at end, before closing div)**

```vue
    <!-- Acquire Modal -->
    <AcquireModal
      v-if="showAcquireModal && selectedBook"
      :book-id="selectedBook.id"
      :book-title="selectedBook.title"
      :value-mid="selectedBook.value_mid"
      @close="closeAcquireModal"
      @acquired="closeAcquireModal"
    />
```

**Step 3: Run frontend tests**

Run: `cd frontend && npm test`
Expected: All tests pass

**Step 4: Commit**

```bash
git add frontend/src/views/AcquisitionsView.vue
git commit -m "feat(ui): Wire acquire modal into dashboard view"
```

---

## Phase 5: Testing and Integration

### Task 5.1: Add Frontend Store Tests

**Files:**
- Create: `frontend/src/stores/__tests__/acquisitions.spec.ts`

**Step 1: Create test file**

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useAcquisitionsStore } from "../acquisitions";
import api from "@/services/api";

vi.mock("@/services/api");
const mockedApi = vi.mocked(api);

describe("acquisitions store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  describe("fetchAll", () => {
    it("fetches books for all three columns", async () => {
      mockedApi.get.mockResolvedValueOnce({ data: { items: [{ id: 1, status: "EVALUATING" }] } });
      mockedApi.get.mockResolvedValueOnce({ data: { items: [{ id: 2, status: "IN_TRANSIT" }] } });
      mockedApi.get.mockResolvedValueOnce({ data: { items: [{ id: 3, status: "ON_HAND", purchase_date: new Date().toISOString() }] } });

      const store = useAcquisitionsStore();
      await store.fetchAll();

      expect(store.evaluating).toHaveLength(1);
      expect(store.inTransit).toHaveLength(1);
      expect(store.received).toHaveLength(1);
      expect(store.loading).toBe(false);
    });

    it("sets error on failure", async () => {
      mockedApi.get.mockRejectedValueOnce(new Error("Network error"));

      const store = useAcquisitionsStore();
      await store.fetchAll();

      expect(store.error).toBe("Network error");
    });
  });

  describe("acquireBook", () => {
    it("moves book from evaluating to inTransit", async () => {
      const store = useAcquisitionsStore();
      store.evaluating = [{ id: 1, title: "Test", status: "EVALUATING" } as any];

      mockedApi.patch.mockResolvedValueOnce({ data: { id: 1, title: "Test", status: "IN_TRANSIT" } });

      await store.acquireBook(1, {
        purchase_price: 100,
        purchase_date: "2025-12-10",
        order_number: "123",
        place_of_purchase: "eBay",
      });

      expect(store.evaluating).toHaveLength(0);
      expect(store.inTransit).toHaveLength(1);
      expect(store.inTransit[0].status).toBe("IN_TRANSIT");
    });
  });

  describe("markReceived", () => {
    it("moves book from inTransit to received", async () => {
      const store = useAcquisitionsStore();
      store.inTransit = [{ id: 1, title: "Test", status: "IN_TRANSIT" } as any];

      mockedApi.patch.mockResolvedValueOnce({ data: { id: 1, title: "Test", status: "ON_HAND" } });

      await store.markReceived(1);

      expect(store.inTransit).toHaveLength(0);
      expect(store.received).toHaveLength(1);
    });
  });
});
```

**Step 2: Run tests**

Run: `cd frontend && npm test`
Expected: All tests pass

**Step 3: Commit**

```bash
git add frontend/src/stores/__tests__/acquisitions.spec.ts
git commit -m "test: Add acquisitions store unit tests"
```

---

### Task 5.2: Run Full Test Suite and Verify

**Step 1: Run backend tests**

```bash
cd backend && .venv/bin/python -m pytest tests -v --tb=short
```
Expected: All tests pass

**Step 2: Run frontend tests**

```bash
cd frontend && npm test
```
Expected: All tests pass

**Step 3: Commit any fixes needed**

If all tests pass:
```bash
git status  # Should be clean
```

---

## Phase 6: Documentation Updates

### Task 6.1: Update CLAUDE.md Acquisition Workflow

**Files:**
- Modify: `CLAUDE.md` (in main project root, not worktree)

**Step 1: Update acquisition workflow section**

Replace the "Acquisition Workflow" section with:

```markdown
## Acquisition Workflow (bmx Dashboard)

### Web Dashboard (Preferred)
Navigate to **https://app.bluemoxon.com/admin/acquisitions** for the visual Kanban board:
- **EVALUATING** → Items being considered (watchlist)
- **IN_TRANSIT** → Purchased, awaiting delivery
- **RECEIVED** → Delivered in last 30 days

### Quick CLI Reference (bmx-api)
```bash
# Add item to watchlist
bmx-api POST /books '{"title":"...", "status":"EVALUATING", ...}'

# Mark as acquired (from dashboard or CLI)
bmx-api PATCH /books/{id}/acquire '{"purchase_price":164.14, "purchase_date":"2025-12-10", "order_number":"...", "place_of_purchase":"eBay"}'

# Mark as received
bmx-api PATCH /books/{id}/status?status=ON_HAND
```

### Deprecated (No Longer Used)
- PRE_ analysis files in local repo
- PENDING_DELIVERIES.txt
- Manual updates to acquisition docs
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: Update CLAUDE.md with acquisitions dashboard workflow"
```

---

## Summary

**Total Tasks:** 15
**Estimated Implementation Time:** ~4-6 hours with TDD approach

**Key Files Created:**
- `backend/app/schemas/book.py` - AcquireRequest, ScoringSnapshot schemas
- `backend/alembic/versions/*_add_acquisition_columns.py` - Migration
- `backend/tests/api/v1/test_acquire.py` - Acquire endpoint tests
- `frontend/src/stores/acquisitions.ts` - Pinia store
- `frontend/src/views/AcquisitionsView.vue` - Dashboard view
- `frontend/src/components/AcquireModal.vue` - Modal component
- `frontend/src/stores/__tests__/acquisitions.spec.ts` - Store tests

**Key Files Modified:**
- `backend/app/models/book.py` - New columns
- `backend/app/api/v1/books.py` - Acquire endpoint
- `frontend/src/router/index.ts` - New route
- `CLAUDE.md` - Updated workflow docs
