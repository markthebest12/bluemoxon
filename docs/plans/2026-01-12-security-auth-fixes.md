# Security Authentication Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add missing authentication to 4 groups of endpoints that currently expose sensitive data without auth.

**Architecture:** Add `Depends(require_viewer)` or `Depends(require_admin)` to endpoint function signatures. All changes are additive - no logic changes, just adding auth dependencies.

**Tech Stack:** FastAPI, pytest, SQLAlchemy

---

## Overview

| Vuln | File | Auth Level | Endpoints |
|------|------|------------|-----------|
| VULN-001 | `export.py` | `require_viewer` | `/csv`, `/json` |
| VULN-002 | `admin.py` | `require_admin` | `/config`, `/system-info`, `/costs` |
| VULN-003 | `stats.py` | `require_viewer` | All 12 endpoints |
| VULN-004 | `books.py` | `require_viewer` | 5 GET endpoints |

**Parallelization:** All 4 vulnerabilities can be fixed in parallel worktrees since they modify different files.

---

## Task 1: VULN-001 - Export Endpoints (CRITICAL)

**Files:**

- Modify: `backend/app/api/v1/export.py`
- Create: `backend/tests/api/v1/test_export_auth.py`

### Step 1.1: Write failing tests for export auth

Create `backend/tests/api/v1/test_export_auth.py`:

```python
"""Tests for export endpoint authentication."""

import pytest
from fastapi.testclient import TestClient

from app.auth import require_viewer
from app.db import get_db
from app.main import app
from app.models.base import Base
from tests.conftest import TestingSessionLocal, engine, get_mock_editor


class TestExportAuth:
    """Tests for export endpoint authentication requirements."""

    @pytest.fixture
    def unauthenticated_client(self, db):
        """Client without auth overrides - simulates unauthenticated request."""

        def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        # Do NOT override require_viewer - this tests real auth
        with TestClient(app) as test_client:
            yield test_client
        app.dependency_overrides.clear()

    @pytest.fixture
    def db(self):
        """Create a fresh database for each test."""
        Base.metadata.create_all(bind=engine)
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
            Base.metadata.drop_all(bind=engine)

    def test_export_csv_requires_auth(self, unauthenticated_client):
        """Test that /export/csv returns 401 without authentication."""
        response = unauthenticated_client.get("/api/v1/export/csv")
        assert response.status_code == 401

    def test_export_json_requires_auth(self, unauthenticated_client):
        """Test that /export/json returns 401 without authentication."""
        response = unauthenticated_client.get("/api/v1/export/json")
        assert response.status_code == 401

    def test_export_csv_works_with_auth(self, client):
        """Test that /export/csv works with authentication."""
        response = client.get("/api/v1/export/csv")
        assert response.status_code == 200

    def test_export_json_works_with_auth(self, client):
        """Test that /export/json works with authentication."""
        response = client.get("/api/v1/export/json")
        assert response.status_code == 200
```

### Step 1.2: Run tests to verify they fail

Run: `poetry run pytest backend/tests/api/v1/test_export_auth.py -v`
Expected: 2 tests fail (auth tests), 2 pass (with mock auth)

### Step 1.3: Add authentication to export endpoints

Modify `backend/app/api/v1/export.py`:

Add import at top:

```python
from app.auth import require_viewer
```

Modify `export_csv` function signature (line 17-21):

```python
@router.get("/csv")
def export_csv(
    inventory_type: str = Query(default="PRIMARY"),
    db: Session = Depends(get_db),
    _user=Depends(require_viewer),
):
```

Modify `export_json` function signature (line 108-112):

```python
@router.get("/json")
def export_json(
    inventory_type: str = Query(default="PRIMARY"),
    db: Session = Depends(get_db),
    _user=Depends(require_viewer),
):
```

### Step 1.4: Run tests to verify they pass

Run: `poetry run pytest backend/tests/api/v1/test_export_auth.py -v`
Expected: All 4 tests PASS

### Step 1.5: Run linting

Run: `poetry run ruff check backend/app/api/v1/export.py backend/tests/api/v1/test_export_auth.py`
Run: `poetry run ruff format backend/app/api/v1/export.py backend/tests/api/v1/test_export_auth.py`

### Step 1.6: Commit

```bash
git add backend/app/api/v1/export.py backend/tests/api/v1/test_export_auth.py
git commit -m "security: Add authentication to export endpoints (VULN-001)

Export CSV and JSON endpoints now require viewer authentication.
Previously allowed unauthenticated access to complete inventory data.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 2: VULN-002 - Admin GET Endpoints (CRITICAL)

**Files:**

- Modify: `backend/app/api/v1/admin.py`
- Create: `backend/tests/api/v1/test_admin_auth.py`

### Step 2.1: Write failing tests for admin GET auth

Create `backend/tests/api/v1/test_admin_auth.py`:

```python
"""Tests for admin GET endpoint authentication."""

import pytest
from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.models.base import Base
from tests.conftest import TestingSessionLocal, engine


class TestAdminGetAuth:
    """Tests for admin GET endpoint authentication requirements."""

    @pytest.fixture
    def unauthenticated_client(self, db):
        """Client without auth overrides - simulates unauthenticated request."""

        def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        with TestClient(app) as test_client:
            yield test_client
        app.dependency_overrides.clear()

    @pytest.fixture
    def db(self):
        """Create a fresh database for each test."""
        Base.metadata.create_all(bind=engine)
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
            Base.metadata.drop_all(bind=engine)

    def test_admin_config_requires_auth(self, unauthenticated_client):
        """Test that GET /admin/config returns 401 without authentication."""
        response = unauthenticated_client.get("/api/v1/admin/config")
        assert response.status_code == 401

    def test_admin_system_info_requires_auth(self, unauthenticated_client):
        """Test that GET /admin/system-info returns 401 without authentication."""
        response = unauthenticated_client.get("/api/v1/admin/system-info")
        assert response.status_code == 401

    def test_admin_costs_requires_auth(self, unauthenticated_client):
        """Test that GET /admin/costs returns 401 without authentication."""
        response = unauthenticated_client.get("/api/v1/admin/costs")
        assert response.status_code == 401

    def test_admin_config_works_with_admin(self, client):
        """Test that GET /admin/config works with admin authentication."""
        response = client.get("/api/v1/admin/config")
        assert response.status_code == 200

    def test_admin_costs_works_with_admin(self, client):
        """Test that GET /admin/costs works with admin authentication."""
        # Mock the cost explorer to avoid AWS calls
        from unittest.mock import patch

        mock_costs = {
            "period_start": "2026-01-01",
            "period_end": "2026-01-12",
            "bedrock_models": [],
            "daily_trend": [],
            "other_services": [],
            "total_mtd": 0.0,
        }
        with patch("app.api.v1.admin.fetch_costs", return_value=mock_costs):
            response = client.get("/api/v1/admin/costs")
            assert response.status_code == 200
```

### Step 2.2: Run tests to verify they fail

Run: `poetry run pytest backend/tests/api/v1/test_admin_auth.py -v`
Expected: 3 auth tests fail, 2 with-auth tests pass

### Step 2.3: Add authentication to admin GET endpoints

Modify `backend/app/api/v1/admin.py`:

Find `get_config` function and add `_user=Depends(require_admin)`:

```python
@router.get("/config", response_model=ConfigResponse)
def get_config(
    response: Response,
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
```

Find `get_system_info` function and add `_user=Depends(require_admin)`:

```python
@router.get("/system-info", response_model=SystemInfoResponse)
def get_system_info(
    response: Response,
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
```

Find `get_costs` function and add `_user=Depends(require_admin)`:

```python
@router.get("/costs", response_model=CostResponse)
def get_costs(
    response: Response,
    timezone: str | None = Query(
        None,
        max_length=64,
        description="IANA timezone name (e.g., 'America/Los_Angeles') for MTD calculation",
    ),
    refresh: bool = False,
    _user=Depends(require_admin),
):
```

### Step 2.4: Run tests to verify they pass

Run: `poetry run pytest backend/tests/api/v1/test_admin_auth.py -v`
Expected: All 5 tests PASS

### Step 2.5: Run linting

Run: `poetry run ruff check backend/app/api/v1/admin.py backend/tests/api/v1/test_admin_auth.py`
Run: `poetry run ruff format backend/app/api/v1/admin.py backend/tests/api/v1/test_admin_auth.py`

### Step 2.6: Commit

```bash
git add backend/app/api/v1/admin.py backend/tests/api/v1/test_admin_auth.py
git commit -m "security: Add authentication to admin GET endpoints (VULN-002)

Admin config, system-info, and costs endpoints now require admin auth.
Previously exposed AWS infrastructure details and billing data.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 3: VULN-003 - Stats Endpoints (HIGH)

**Files:**

- Modify: `backend/app/api/v1/stats.py`
- Create: `backend/tests/api/v1/test_stats_auth.py`

### Step 3.1: Write failing tests for stats auth

Create `backend/tests/api/v1/test_stats_auth.py`:

```python
"""Tests for stats endpoint authentication."""

import pytest
from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.models.base import Base
from tests.conftest import TestingSessionLocal, engine


STATS_ENDPOINTS = [
    "/api/v1/stats/overview",
    "/api/v1/stats/metrics",
    "/api/v1/stats/by-category",
    "/api/v1/stats/by-condition",
    "/api/v1/stats/by-publisher",
    "/api/v1/stats/by-author",
    "/api/v1/stats/bindings",
    "/api/v1/stats/by-era",
    "/api/v1/stats/pending-deliveries",
    "/api/v1/stats/acquisitions-by-month",
    "/api/v1/stats/acquisitions-daily",
    "/api/v1/stats/dashboard",
]


class TestStatsAuth:
    """Tests for stats endpoint authentication requirements."""

    @pytest.fixture
    def unauthenticated_client(self, db):
        """Client without auth overrides - simulates unauthenticated request."""

        def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        with TestClient(app) as test_client:
            yield test_client
        app.dependency_overrides.clear()

    @pytest.fixture
    def db(self):
        """Create a fresh database for each test."""
        Base.metadata.create_all(bind=engine)
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
            Base.metadata.drop_all(bind=engine)

    @pytest.mark.parametrize("endpoint", STATS_ENDPOINTS)
    def test_stats_endpoint_requires_auth(self, unauthenticated_client, endpoint):
        """Test that stats endpoints return 401 without authentication."""
        response = unauthenticated_client.get(endpoint)
        assert response.status_code == 401, f"{endpoint} should require auth"

    @pytest.mark.parametrize("endpoint", STATS_ENDPOINTS)
    def test_stats_endpoint_works_with_auth(self, client, endpoint):
        """Test that stats endpoints work with authentication."""
        response = client.get(endpoint)
        assert response.status_code == 200, f"{endpoint} should work with auth"
```

### Step 3.2: Run tests to verify they fail

Run: `poetry run pytest backend/tests/api/v1/test_stats_auth.py -v`
Expected: 12 auth tests fail, 12 with-auth tests pass

### Step 3.3: Add authentication to all stats endpoints

Modify `backend/app/api/v1/stats.py`:

Add import at top:

```python
from app.auth import require_viewer
```

Add `_user=Depends(require_viewer)` parameter to ALL endpoint functions:

- `get_overview`
- `get_metrics`
- `get_by_category`
- `get_by_condition`
- `get_by_publisher`
- `get_by_author`
- `get_bindings`
- `get_by_era`
- `get_pending_deliveries`
- `get_acquisitions_by_month`
- `get_acquisitions_daily`
- `get_dashboard`

Example for each:

```python
@router.get("/overview")
def get_overview(
    db: Session = Depends(get_db),
    _user=Depends(require_viewer),
):
```

### Step 3.4: Run tests to verify they pass

Run: `poetry run pytest backend/tests/api/v1/test_stats_auth.py -v`
Expected: All 24 tests PASS

### Step 3.5: Run linting

Run: `poetry run ruff check backend/app/api/v1/stats.py backend/tests/api/v1/test_stats_auth.py`
Run: `poetry run ruff format backend/app/api/v1/stats.py backend/tests/api/v1/test_stats_auth.py`

### Step 3.6: Commit

```bash
git add backend/app/api/v1/stats.py backend/tests/api/v1/test_stats_auth.py
git commit -m "security: Add authentication to stats endpoints (VULN-003)

All stats endpoints now require viewer authentication.
Previously exposed business intelligence and financial metrics.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 4: VULN-004 - Books GET Endpoints (HIGH)

**Files:**

- Modify: `backend/app/api/v1/books.py`
- Create: `backend/tests/api/v1/test_books_auth.py`

### Step 4.1: Write failing tests for books GET auth

Create `backend/tests/api/v1/test_books_auth.py`:

```python
"""Tests for books GET endpoint authentication."""

import pytest
from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.models import Author, Book
from app.models.base import Base
from tests.conftest import TestingSessionLocal, engine


class TestBooksGetAuth:
    """Tests for books GET endpoint authentication requirements."""

    @pytest.fixture
    def unauthenticated_client(self, db):
        """Client without auth overrides - simulates unauthenticated request."""

        def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        with TestClient(app) as test_client:
            yield test_client
        app.dependency_overrides.clear()

    @pytest.fixture
    def db(self):
        """Create a fresh database for each test."""
        Base.metadata.create_all(bind=engine)
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
            Base.metadata.drop_all(bind=engine)

    @pytest.fixture
    def sample_book(self, db):
        """Create a sample book for testing."""
        author = Author(name="Test Author")
        db.add(author)
        db.flush()

        book = Book(
            title="Test Book",
            author_id=author.id,
            inventory_type="PRIMARY",
            status="ON_HAND",
        )
        db.add(book)
        db.commit()
        db.refresh(book)
        return book

    def test_books_list_requires_auth(self, unauthenticated_client):
        """Test that GET /books returns 401 without authentication."""
        response = unauthenticated_client.get("/api/v1/books")
        assert response.status_code == 401

    def test_books_get_requires_auth(self, unauthenticated_client, sample_book):
        """Test that GET /books/{id} returns 401 without authentication."""
        response = unauthenticated_client.get(f"/api/v1/books/{sample_book.id}")
        assert response.status_code == 401

    def test_books_analysis_requires_auth(self, unauthenticated_client, sample_book):
        """Test that GET /books/{id}/analysis returns 401 without authentication."""
        response = unauthenticated_client.get(f"/api/v1/books/{sample_book.id}/analysis")
        assert response.status_code == 401

    def test_books_analysis_raw_requires_auth(self, unauthenticated_client, sample_book):
        """Test that GET /books/{id}/analysis/raw returns 401 without authentication."""
        response = unauthenticated_client.get(
            f"/api/v1/books/{sample_book.id}/analysis/raw"
        )
        assert response.status_code == 401

    def test_books_scores_breakdown_requires_auth(
        self, unauthenticated_client, sample_book
    ):
        """Test that GET /books/{id}/scores/breakdown returns 401 without authentication."""
        response = unauthenticated_client.get(
            f"/api/v1/books/{sample_book.id}/scores/breakdown"
        )
        assert response.status_code == 401

    def test_books_list_works_with_auth(self, client):
        """Test that GET /books works with authentication."""
        response = client.get("/api/v1/books")
        assert response.status_code == 200

    def test_books_get_works_with_auth(self, client, sample_book):
        """Test that GET /books/{id} works with authentication."""
        response = client.get(f"/api/v1/books/{sample_book.id}")
        assert response.status_code == 200
```

### Step 4.2: Run tests to verify they fail

Run: `poetry run pytest backend/tests/api/v1/test_books_auth.py -v`
Expected: 5 auth tests fail, 2 with-auth tests pass

### Step 4.3: Add authentication to books GET endpoints

Modify `backend/app/api/v1/books.py`:

Add import (if not present):

```python
from app.auth import require_admin, require_editor, require_viewer
```

Add `_user=Depends(require_viewer)` to these endpoints:

1. `list_books` (GET /books):

```python
@router.get("", response_model=BookListResponse)
def list_books(
    params: Annotated[BookListParams, Depends()],
    response: Response,
    db: Session = Depends(get_db),
    _user=Depends(require_viewer),
):
```

1. `get_book` (GET /books/{book_id}):

```python
@router.get("/{book_id}", response_model=BookResponse)
def get_book(
    book_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_viewer),
):
```

1. `get_book_analysis` (GET /books/{book_id}/analysis):

```python
@router.get("/{book_id}/analysis")
def get_book_analysis(
    book_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_viewer),
):
```

1. `get_book_analysis_raw` (GET /books/{book_id}/analysis/raw):

```python
@router.get("/{book_id}/analysis/raw")
def get_book_analysis_raw(
    book_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_viewer),
):
```

1. `get_scores_breakdown` (GET /books/{book_id}/scores/breakdown):

```python
@router.get("/{book_id}/scores/breakdown")
def get_scores_breakdown(
    book_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_viewer),
):
```

### Step 4.4: Run tests to verify they pass

Run: `poetry run pytest backend/tests/api/v1/test_books_auth.py -v`
Expected: All 7 tests PASS

### Step 4.5: Run linting

Run: `poetry run ruff check backend/app/api/v1/books.py backend/tests/api/v1/test_books_auth.py`
Run: `poetry run ruff format backend/app/api/v1/books.py backend/tests/api/v1/test_books_auth.py`

### Step 4.6: Commit

```bash
git add backend/app/api/v1/books.py backend/tests/api/v1/test_books_auth.py
git commit -m "security: Add authentication to books GET endpoints (VULN-004)

Books list, detail, analysis, and scores endpoints now require viewer auth.
Previously exposed financial data (purchase prices, valuations, ROI).

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Final Validation

### Step 5.1: Run all tests

Run: `poetry run pytest backend/tests/ -v`
Expected: All tests PASS

### Step 5.2: Run full linting

Run: `poetry run ruff check backend/`
Run: `poetry run ruff format --check backend/`

### Step 5.3: Create PR to staging

```bash
git push -u origin fix/security-auth-endpoints
gh pr create --base staging --title "security: Add authentication to unauthenticated endpoints" --body "## Summary
- VULN-001: Export endpoints now require viewer auth
- VULN-002: Admin GET endpoints now require admin auth
- VULN-003: Stats endpoints now require viewer auth
- VULN-004: Books GET endpoints now require viewer auth

## Test Plan
- [ ] All new auth tests pass
- [ ] Existing tests pass
- [ ] Manual verification in staging

## Security
Fixes critical unauthenticated data exposure vulnerabilities identified in security review."
```

---

## Execution Strategy

**Recommended: Parallel Worktrees**

Since all 4 vulnerabilities modify different files, they can be fixed in parallel:

```
Worktree 1: fix/vuln-001-export-auth (Task 1)
Worktree 2: fix/vuln-002-admin-auth (Task 2)
Worktree 3: fix/vuln-003-stats-auth (Task 3)
Worktree 4: fix/vuln-004-books-auth (Task 4)
```

Each worktree runs TDD cycle independently, then merge all to single PR for staging.
