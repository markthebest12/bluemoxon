# Wave 3: Cache Social Circles Graph + Async Batch Generation

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Eliminate redundant graph builds on every profile view (#1549) and convert synchronous batch generation to async SQS + Lambda worker (#1550).

**Architecture:** Two layers of caching for the social circles graph (Redis cross-request cache + pass-through within request). Batch generation dispatches one SQS message per entity to a dedicated worker Lambda, with a new `profile_generation_jobs` table for progress tracking.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Redis (ElastiCache), SQS, Lambda, Terraform, pytest

**Issues:** #1549, #1550

**Branches:** `feat/ep-wave3` (code, both issues), `feat/ep-wave3-infra` (Terraform module)

---

## Parallelization Strategy

Two independent worktrees:

| Worktree | Branch | Content | Dependency |
|----------|--------|---------|------------|
| `.tmp/worktrees/wave3` | `feat/ep-wave3` | Tasks 1-6 (all Python code) | None |
| `.tmp/worktrees/wave3-infra` | `feat/ep-wave3-infra` | Task 7 (Terraform module) | None |

Within the code worktree, Tasks 1-3 (#1549 cache) must complete before Tasks 4-6 (#1550 async) since the worker uses the cached graph. Task 7 (infra) is fully independent.

**Two PRs:**
- PR A: `feat/ep-wave3` -> staging (code)
- PR B: `feat/ep-wave3-infra` -> staging (infrastructure)

PR B can merge first (infrastructure deployed before code). PR A depends on PR B being deployed so the queue exists when the code ships.

---

## Task 1: Sync cache wrapper for social circles graph (#1549)

**Files:**
- Modify: `backend/app/services/social_circles_cache.py` (add sync function after line 57)
- Test: `backend/tests/test_social_circles_cache.py` (create or modify)

**Context:** The async cache functions (`get_cached_graph`, `set_cached_graph`) already exist but use `asyncio.get_running_loop()`. Entity profile service is sync code. We need a sync wrapper that calls `_get_cached_graph_sync` and `_set_cached_graph_sync` directly (these already exist at lines 60-82 and 107-132).

**Step 1: Write failing test**

```python
# tests/test_social_circles_cache.py

from unittest.mock import MagicMock, patch

from app.services.social_circles_cache import get_or_build_graph


class TestGetOrBuildGraph:
    """Tests for sync cache wrapper."""

    @patch("app.services.social_circles_cache.get_redis")
    @patch("app.services.social_circles_cache.build_social_circles_graph")
    def test_returns_cached_graph_on_hit(self, mock_build, mock_redis):
        """Cache hit returns cached graph without calling build."""
        cached_response = MagicMock()
        client = MagicMock()
        # Simulate cache hit: _get_cached_graph_sync returns (response, True)
        import json
        client.get.return_value = json.dumps({"nodes": [], "edges": [], "meta": {"node_count": 0, "edge_count": 0, "truncated": False, "generated_at": "2026-01-01T00:00:00"}})
        mock_redis.return_value = client

        db = MagicMock()
        result = get_or_build_graph(db)

        mock_build.assert_not_called()
        assert result is not None

    @patch("app.services.social_circles_cache.get_redis")
    @patch("app.services.social_circles_cache.build_social_circles_graph")
    def test_builds_and_caches_on_miss(self, mock_build, mock_redis):
        """Cache miss builds graph and caches it."""
        client = MagicMock()
        client.get.return_value = None  # Cache miss
        mock_redis.return_value = client
        mock_build.return_value = MagicMock()
        mock_build.return_value.model_dump.return_value = {"nodes": [], "edges": [], "meta": {}}

        db = MagicMock()
        result = get_or_build_graph(db)

        mock_build.assert_called_once_with(db)
        assert result == mock_build.return_value

    @patch("app.services.social_circles_cache.get_redis")
    @patch("app.services.social_circles_cache.build_social_circles_graph")
    def test_builds_without_caching_when_no_redis(self, mock_build, mock_redis):
        """No Redis client: build graph, skip caching."""
        mock_redis.return_value = None
        mock_build.return_value = MagicMock()

        db = MagicMock()
        result = get_or_build_graph(db)

        mock_build.assert_called_once_with(db)
        assert result == mock_build.return_value
```

**Step 2: Run test to verify it fails**

```bash
cd backend
poetry run python -m pytest tests/test_social_circles_cache.py::TestGetOrBuildGraph -v
```

Expected: FAIL — `ImportError: cannot import name 'get_or_build_graph'`

**Step 3: Write minimal implementation**

Add to `backend/app/services/social_circles_cache.py` after the `get_cache_key` function (after line 57):

```python
def get_or_build_graph(db: Session) -> SocialCirclesResponse:
    """Get social circles graph from cache or build it.

    Sync wrapper for use in entity_profile service. Checks Redis first,
    builds on miss and caches. Degrades gracefully if Redis unavailable.

    Args:
        db: Database session for building the graph on cache miss.

    Returns:
        SocialCirclesResponse with all nodes and edges.
    """
    from app.services.social_circles import build_social_circles_graph

    cache_key = get_cache_key(include_binders=True, min_book_count=1, max_books=5000)
    client = get_redis()

    if client:
        cached, is_hit = _get_cached_graph_sync(client, cache_key)
        if is_hit and cached:
            return cached

    graph = build_social_circles_graph(db)

    if client:
        _set_cached_graph_sync(client, cache_key, graph)

    return graph
```

Also add the `TYPE_CHECKING` import for `Session` at the top:

```python
if TYPE_CHECKING:
    from redis import Redis
    from sqlalchemy.orm import Session
```

**Step 4: Run tests to verify they pass**

```bash
cd backend
poetry run python -m pytest tests/test_social_circles_cache.py::TestGetOrBuildGraph -v
```

Expected: 3 PASSED

**Step 5: Lint and commit**

```bash
poetry run ruff check backend/app/services/social_circles_cache.py backend/tests/test_social_circles_cache.py
poetry run ruff format backend/app/services/social_circles_cache.py backend/tests/test_social_circles_cache.py
git add backend/app/services/social_circles_cache.py backend/tests/test_social_circles_cache.py
git commit -m "feat: add sync cache wrapper for social circles graph (#1549)"
```

---

## Task 2: Wire cached graph into entity profile service (#1549)

**Files:**
- Modify: `backend/app/services/entity_profile.py:179` (`_build_connections` signature)
- Modify: `backend/app/services/entity_profile.py:325` (`get_entity_profile`)
- Modify: `backend/app/services/entity_profile.py:370` (`generate_and_cache_profile` signature)
- Modify: `backend/app/api/v1/entity_profile.py:98` (`regenerate_profile`)
- Test: `backend/tests/test_entity_profile.py`

**Context:** Currently `_build_connections` and `generate_and_cache_profile` each call `build_social_circles_graph(db)` directly. We add an optional `graph` parameter to both, and the callers build once via `get_or_build_graph(db)` and pass it through.

**Step 1: Write failing tests**

```python
# Add to tests/test_entity_profile.py

class TestCachedGraphPassThrough:
    """Tests for graph caching pass-through (#1549)."""

    @patch("app.services.entity_profile.get_or_build_graph")
    @patch("app.services.entity_profile.build_social_circles_graph")
    def test_build_connections_uses_provided_graph(self, mock_build, mock_cached, db):
        """_build_connections skips build when graph is provided."""
        graph = MagicMock()
        graph.edges = []
        graph.nodes = []

        _build_connections(db, "author", 999, None, graph=graph)

        mock_build.assert_not_called()
        mock_cached.assert_not_called()

    @patch("app.services.entity_profile.get_or_build_graph")
    @patch("app.services.entity_profile.build_social_circles_graph")
    def test_build_connections_calls_cache_when_no_graph(self, mock_build, mock_cached, db):
        """_build_connections uses get_or_build_graph when no graph provided."""
        cached_graph = MagicMock()
        cached_graph.edges = []
        cached_graph.nodes = []
        mock_cached.return_value = cached_graph

        _build_connections(db, "author", 999, None)

        mock_cached.assert_called_once_with(db)
        mock_build.assert_not_called()

    @patch("app.services.entity_profile.get_or_build_graph")
    def test_get_entity_profile_passes_graph_to_build_connections(self, mock_cached, db):
        """get_entity_profile builds graph once and passes to _build_connections."""
        # Setup: create an author so get_entity_profile doesn't return None
        from app.models.author import Author
        author = Author(name="Cache Test Author")
        db.add(author)
        db.flush()
        from app.models.user import User
        user = User(cognito_sub="cache-test", email="cache@example.com", role="viewer")
        db.add(user)
        db.flush()
        db.commit()

        cached_graph = MagicMock()
        cached_graph.edges = []
        cached_graph.nodes = []
        mock_cached.return_value = cached_graph

        get_entity_profile(db, "author", author.id, user.id)

        # get_or_build_graph called exactly once (not twice)
        mock_cached.assert_called_once_with(db)
```

**Step 2: Run tests to verify they fail**

```bash
cd backend
poetry run python -m pytest tests/test_entity_profile.py::TestCachedGraphPassThrough -v
```

Expected: FAIL — `graph` parameter not accepted

**Step 3: Implement changes**

In `backend/app/services/entity_profile.py`:

1. Add import at top:
```python
from app.services.social_circles_cache import get_or_build_graph
```

2. Change `_build_connections` signature (line 179):
```python
def _build_connections(
    db: Session,
    entity_type: str,
    entity_id: int,
    profile: EntityProfile | None,
    graph: SocialCirclesResponse | None = None,
) -> list[ProfileConnection]:
```

3. Replace `graph = build_social_circles_graph(db)` (line 193) with:
```python
    if graph is None:
        graph = get_or_build_graph(db)
```

4. Change `generate_and_cache_profile` signature (line 370):
```python
def generate_and_cache_profile(
    db: Session,
    entity_type: str,
    entity_id: int,
    owner_id: int,
    max_narratives: int | None = None,
    graph: SocialCirclesResponse | None = None,
) -> EntityProfile:
```

5. Replace `graph = build_social_circles_graph(db)` (line ~397) with:
```python
    if graph is None:
        graph = get_or_build_graph(db)
```

6. In `get_entity_profile` (line 325), build the graph once and pass through:
```python
def get_entity_profile(...):
    ...
    graph = get_or_build_graph(db)
    connections = _build_connections(db, entity_type, entity_id, cached, graph=graph)
    ...
```

7. In `regenerate_profile` endpoint (`api/v1/entity_profile.py:108`), pass graph:
```python
    graph = get_or_build_graph(db)
    generate_and_cache_profile(db, entity_type.value, entity_id, current_user.db_user.id, graph=graph)
```

Add the import to the API file:
```python
from app.services.social_circles_cache import get_or_build_graph
```

8. Remove the now-unused import of `build_social_circles_graph` from entity_profile.py service (if no longer needed directly).

**Step 4: Run all entity profile tests**

```bash
cd backend
poetry run python -m pytest tests/test_entity_profile.py -v
```

Expected: ALL PASSED (existing tests use mocks for `build_social_circles_graph` — update mock targets if needed to `get_or_build_graph`)

**Step 5: Lint and commit**

```bash
poetry run ruff check backend/app/services/entity_profile.py backend/app/api/v1/entity_profile.py backend/tests/test_entity_profile.py
poetry run ruff format backend/app/services/entity_profile.py backend/app/api/v1/entity_profile.py backend/tests/test_entity_profile.py
git add backend/app/services/entity_profile.py backend/app/api/v1/entity_profile.py backend/tests/test_entity_profile.py
git commit -m "feat: wire cached graph into entity profile service (#1549)"
```

**Important:** Existing tests that mock `build_social_circles_graph` will need their mock target updated. The existing test classes (`TestBuildConnectionsClassifier`, etc.) all `@patch("app.services.entity_profile.build_social_circles_graph")`. These need to change to `@patch("app.services.entity_profile.get_or_build_graph")` since `_build_connections` will now call `get_or_build_graph` instead of `build_social_circles_graph` when no graph is provided.

---

## Task 3: ProfileGenerationJob model + migration (#1550)

**Files:**
- Create: `backend/app/models/profile_generation_job.py`
- Create: `backend/alembic/versions/<rev>_add_profile_generation_jobs.py`
- Modify: `backend/app/db/migration_sql.py` (register migration)
- Test: migration sync validation

**Step 1: Write the model**

```python
# backend/app/models/profile_generation_job.py
"""Profile generation job model -- tracks async batch profile generation."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ProfileGenerationJob(TimestampMixin, Base):
    """Tracks progress of async batch profile generation."""

    __tablename__ = "profile_generation_jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    total_entities: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    succeeded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_log: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

**Step 2: Create Alembic migration**

```bash
cd backend
poetry run alembic revision --autogenerate -m "add profile_generation_jobs table"
```

Verify the generated migration creates the `profile_generation_jobs` table with all columns.

**Step 3: Register in migration_sql.py**

Add the migration SQL and register in the `MIGRATIONS` list at the bottom of `backend/app/db/migration_sql.py`. Follow the existing pattern.

**Step 4: Validate migration sync**

```bash
cd backend
poetry run python scripts/validate_migration_sync.py
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/models/profile_generation_job.py backend/alembic/versions/ backend/app/db/migration_sql.py
git commit -m "feat: add ProfileGenerationJob model and migration (#1550)"
```

---

## Task 4: SQS dispatch functions (#1550)

**Files:**
- Modify: `backend/app/services/sqs.py` (add profile generation queue functions)
- Modify: `backend/app/config.py` (add queue name setting)
- Test: `backend/tests/test_sqs.py` (create or modify)

**Step 1: Write failing tests**

```python
# tests/test_sqs.py (add to existing or create)

from unittest.mock import MagicMock, patch
from app.services.sqs import get_profile_generation_queue_url, send_profile_generation_jobs


class TestProfileGenerationQueue:
    @patch("app.services.sqs.settings")
    @patch("app.services.sqs._get_queue_url")
    def test_get_queue_url(self, mock_get_url, mock_settings):
        mock_settings.profile_generation_queue_name = "test-queue"
        mock_get_url.return_value = "https://sqs.us-east-1.amazonaws.com/123/test-queue"

        url = get_profile_generation_queue_url()
        assert url == "https://sqs.us-east-1.amazonaws.com/123/test-queue"

    @patch("app.services.sqs.settings")
    def test_get_queue_url_raises_when_not_configured(self, mock_settings):
        mock_settings.profile_generation_queue_name = None
        import pytest
        with pytest.raises(ValueError, match="PROFILE_GENERATION_QUEUE_NAME"):
            get_profile_generation_queue_url()

    @patch("app.services.sqs.get_profile_generation_queue_url")
    @patch("app.services.sqs.get_sqs_client")
    def test_send_jobs_batches_messages(self, mock_client_fn, mock_url):
        """Messages are sent in batches of 10 via send_message_batch."""
        client = MagicMock()
        client.send_message_batch.return_value = {"Successful": [], "Failed": []}
        mock_client_fn.return_value = client
        mock_url.return_value = "https://sqs/queue"

        messages = [
            {"job_id": "j1", "entity_type": "author", "entity_id": i, "owner_id": 1}
            for i in range(25)
        ]
        send_profile_generation_jobs(messages)

        # 25 messages = 3 batches (10 + 10 + 5)
        assert client.send_message_batch.call_count == 3
```

**Step 2: Run tests to verify they fail**

**Step 3: Add config setting**

In `backend/app/config.py` after `image_processing_queue_name` (line ~185):

```python
    # Profile generation worker queue
    profile_generation_queue_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "BMX_PROFILE_GENERATION_QUEUE_NAME", "PROFILE_GENERATION_QUEUE_NAME"
        ),
    )
```

**Step 4: Add SQS functions**

In `backend/app/services/sqs.py`:

```python
def get_profile_generation_queue_url() -> str:
    """Get the profile generation jobs queue URL."""
    queue_name = settings.profile_generation_queue_name
    if not queue_name:
        raise ValueError("PROFILE_GENERATION_QUEUE_NAME environment variable not set")
    return _get_queue_url(queue_name)


def send_profile_generation_jobs(messages: list[dict]) -> None:
    """Send profile generation job messages to SQS in batches.

    Args:
        messages: List of dicts with keys: job_id, entity_type, entity_id, owner_id
    """
    sqs = get_sqs_client()
    queue_url = get_profile_generation_queue_url()

    for i in range(0, len(messages), 10):
        batch = messages[i : i + 10]
        entries = [
            {
                "Id": str(idx),
                "MessageBody": json.dumps(msg),
            }
            for idx, msg in enumerate(batch)
        ]

        response = sqs.send_message_batch(QueueUrl=queue_url, Entries=entries)

        failed = response.get("Failed", [])
        if failed:
            logger.error("Failed to send %d profile generation messages: %s", len(failed), failed)
```

**Step 5: Run tests, lint, commit**

```bash
poetry run python -m pytest tests/test_sqs.py::TestProfileGenerationQueue -v
poetry run ruff check backend/app/services/sqs.py backend/app/config.py
poetry run ruff format backend/app/services/sqs.py backend/app/config.py
git add backend/app/services/sqs.py backend/app/config.py backend/tests/test_sqs.py
git commit -m "feat: add SQS dispatch for profile generation jobs (#1550)"
```

---

## Task 5: Rewrite batch endpoint + add status endpoint (#1550)

**Files:**
- Modify: `backend/app/api/v1/entity_profile.py:24-67` (rewrite `generate_all_profiles`)
- Modify: `backend/app/api/v1/entity_profile.py` (add status endpoint)
- Test: `backend/tests/test_entity_profile.py`

**Step 1: Write failing tests**

```python
# Add to tests/test_entity_profile.py

class TestGenerateAllAsync:
    """Tests for async batch generation endpoint (#1550)."""

    @patch("app.api.v1.entity_profile.send_profile_generation_jobs")
    def test_generate_all_returns_job_id(self, mock_send, client_admin, db):
        """POST /generate-all returns job_id and enqueues messages."""
        from app.models.author import Author
        author = Author(name="Batch Author")
        db.add(author)
        db.commit()

        response = client_admin.post("/api/v1/profiles/generate-all")
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"
        assert data["total_entities"] >= 1
        mock_send.assert_called_once()

    @patch("app.api.v1.entity_profile.send_profile_generation_jobs")
    def test_generate_all_rejects_when_job_in_progress(self, mock_send, client_admin, db):
        """Returns existing job if one is already in progress."""
        from app.models.profile_generation_job import ProfileGenerationJob
        from app.models.author import Author
        author = Author(name="Existing Author")
        db.add(author)
        db.flush()
        job = ProfileGenerationJob(
            owner_id=1, status="in_progress", total_entities=5
        )
        db.add(job)
        db.commit()

        response = client_admin.post("/api/v1/profiles/generate-all")
        data = response.json()
        assert data["job_id"] == job.id
        assert data["status"] == "in_progress"
        mock_send.assert_not_called()


class TestGenerateAllStatus:
    """Tests for batch generation status endpoint (#1550)."""

    def test_status_returns_job_progress(self, client_admin, db):
        from app.models.profile_generation_job import ProfileGenerationJob
        job = ProfileGenerationJob(
            owner_id=1, status="in_progress", total_entities=10, succeeded=7, failed=1
        )
        db.add(job)
        db.commit()

        response = client_admin.get(f"/api/v1/profiles/generate-all/status/{job.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total_entities"] == 10
        assert data["succeeded"] == 7
        assert data["failed"] == 1

    def test_status_404_for_unknown_job(self, client_admin):
        response = client_admin.get("/api/v1/profiles/generate-all/status/nonexistent-id")
        assert response.status_code == 404
```

**Step 2: Run tests to verify they fail**

**Step 3: Implement the endpoints**

Rewrite `backend/app/api/v1/entity_profile.py`. Replace the sync `generate_all_profiles` with:

```python
@router.post(
    "/profiles/generate-all",
    summary="Generate all entity profiles (async)",
    description="Admin-only: enqueues async profile generation for all entities.",
)
def generate_all_profiles(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Enqueue async profile generation for all entities.

    Returns a job ID for progress tracking. If an in-progress job exists,
    returns that job instead of creating a new one.
    """
    if not current_user.db_user:
        raise HTTPException(status_code=403, detail="API key auth requires linked database user")

    # Check for existing in-progress job
    existing = (
        db.query(ProfileGenerationJob)
        .filter(ProfileGenerationJob.status.in_(["pending", "in_progress"]))
        .first()
    )
    if existing:
        return {
            "job_id": existing.id,
            "total_entities": existing.total_entities,
            "status": existing.status,
        }

    # Collect all entities
    entities = []
    for entity_type, model in [("author", Author), ("publisher", Publisher), ("binder", Binder)]:
        for entity in db.query(model).all():
            entities.append((entity_type, entity.id))

    # Create job record
    job = ProfileGenerationJob(
        owner_id=current_user.db_user.id,
        status="pending",
        total_entities=len(entities),
    )
    db.add(job)
    db.commit()

    # Enqueue SQS messages
    messages = [
        {
            "job_id": job.id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "owner_id": current_user.db_user.id,
        }
        for entity_type, entity_id in entities
    ]
    send_profile_generation_jobs(messages)

    return {
        "job_id": job.id,
        "total_entities": len(entities),
        "status": "pending",
    }
```

Add status endpoint:

```python
@router.get(
    "/profiles/generate-all/status/{job_id}",
    summary="Get batch generation job status",
)
def get_generation_status(
    job_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Get progress of a batch profile generation job."""
    job = db.query(ProfileGenerationJob).filter(ProfileGenerationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return {
        "job_id": job.id,
        "status": job.status,
        "total_entities": job.total_entities,
        "succeeded": job.succeeded,
        "failed": job.failed,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }
```

Add imports to the API file:
```python
from app.models.profile_generation_job import ProfileGenerationJob
from app.services.sqs import send_profile_generation_jobs
```

Remove `import time` (no longer needed).

**Step 4: Run tests, lint, commit**

```bash
poetry run python -m pytest tests/test_entity_profile.py::TestGenerateAllAsync tests/test_entity_profile.py::TestGenerateAllStatus -v
poetry run ruff check backend/app/api/v1/entity_profile.py
poetry run ruff format backend/app/api/v1/entity_profile.py
git add backend/app/api/v1/entity_profile.py backend/app/models/profile_generation_job.py backend/tests/test_entity_profile.py
git commit -m "feat: rewrite batch generation as async SQS dispatch (#1550)"
```

---

## Task 6: Profile worker Lambda handler (#1550)

**Files:**
- Create: `backend/app/services/profile_worker.py`
- Test: `backend/tests/test_profile_worker.py`

**Step 1: Write failing tests**

```python
# tests/test_profile_worker.py

from unittest.mock import MagicMock, patch
import json
import pytest

from app.services.profile_worker import handle_profile_generation_message


class TestProfileWorker:
    """Tests for profile generation worker handler."""

    @patch("app.services.profile_worker.get_or_build_graph")
    @patch("app.services.profile_worker.generate_and_cache_profile")
    @patch("app.services.profile_worker._update_job_progress")
    def test_success_increments_succeeded(self, mock_update, mock_gen, mock_graph, db):
        """Successful generation increments succeeded count."""
        mock_graph.return_value = MagicMock()
        mock_gen.return_value = MagicMock()

        message = {
            "job_id": "test-job-1",
            "entity_type": "author",
            "entity_id": 1,
            "owner_id": 1,
        }

        handle_profile_generation_message(message, db)

        mock_gen.assert_called_once()
        mock_update.assert_called_once_with(db, "test-job-1", success=True)

    @patch("app.services.profile_worker.get_or_build_graph")
    @patch("app.services.profile_worker.generate_and_cache_profile")
    @patch("app.services.profile_worker._update_job_progress")
    def test_failure_increments_failed(self, mock_update, mock_gen, mock_graph, db):
        """Failed generation increments failed count."""
        mock_graph.return_value = MagicMock()
        mock_gen.side_effect = Exception("Bedrock error")

        message = {
            "job_id": "test-job-1",
            "entity_type": "author",
            "entity_id": 1,
            "owner_id": 1,
        }

        handle_profile_generation_message(message, db)

        mock_update.assert_called_once_with(db, "test-job-1", success=False)

    @patch("app.services.profile_worker.get_or_build_graph")
    @patch("app.services.profile_worker._check_staleness")
    @patch("app.services.profile_worker.generate_and_cache_profile")
    @patch("app.services.profile_worker._update_job_progress")
    def test_skips_non_stale_entity(self, mock_update, mock_gen, mock_stale, mock_graph, db):
        """Non-stale entity is skipped (idempotency)."""
        mock_graph.return_value = MagicMock()
        mock_stale.return_value = False  # Not stale = already generated

        message = {
            "job_id": "test-job-1",
            "entity_type": "author",
            "entity_id": 1,
            "owner_id": 1,
        }

        handle_profile_generation_message(message, db)

        mock_gen.assert_not_called()
        mock_update.assert_called_once_with(db, "test-job-1", success=True)
```

**Step 2: Run tests to verify they fail**

**Step 3: Implement the worker**

```python
# backend/app/services/profile_worker.py
"""Profile generation worker -- processes SQS messages for async batch generation."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import text

from app.models.entity_profile import EntityProfile
from app.models.profile_generation_job import ProfileGenerationJob
from app.services.entity_profile import generate_and_cache_profile
from app.services.social_circles_cache import get_or_build_graph

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _check_staleness(db: Session, entity_type: str, entity_id: int, owner_id: int) -> bool:
    """Check if entity needs profile generation.

    Returns True if entity has no profile or profile is stale.
    """
    profile = (
        db.query(EntityProfile)
        .filter(
            EntityProfile.entity_type == entity_type,
            EntityProfile.entity_id == entity_id,
            EntityProfile.owner_id == owner_id,
        )
        .first()
    )
    if not profile or not profile.generated_at:
        return True  # No profile = needs generation

    from app.services.entity_profile import _check_staleness as check_stale
    return check_stale(db, profile, entity_type, entity_id)


def _update_job_progress(db: Session, job_id: str, success: bool) -> None:
    """Atomically update job progress and check for completion."""
    column = "succeeded" if success else "failed"
    db.execute(
        text(f"UPDATE profile_generation_jobs SET {column} = {column} + 1 WHERE id = :job_id"),
        {"job_id": job_id},
    )
    db.commit()

    # Check completion
    job = db.query(ProfileGenerationJob).filter(ProfileGenerationJob.id == job_id).first()
    if job and (job.succeeded + job.failed) >= job.total_entities:
        job.status = "completed"
        job.completed_at = datetime.now(UTC)
        db.commit()


def handle_profile_generation_message(message: dict, db: Session) -> None:
    """Process a single profile generation message.

    Args:
        message: Dict with keys: job_id, entity_type, entity_id, owner_id
        db: Database session
    """
    job_id = message["job_id"]
    entity_type = message["entity_type"]
    entity_id = message["entity_id"]
    owner_id = message["owner_id"]

    try:
        # Idempotency: skip if entity already has a non-stale profile
        if not _check_staleness(db, entity_type, entity_id, owner_id):
            logger.info("Skipping %s:%s (profile is current)", entity_type, entity_id)
            _update_job_progress(db, job_id, success=True)
            return

        # Get cached graph (first worker builds, rest get cache hits)
        graph = get_or_build_graph(db)

        # Generate profile
        generate_and_cache_profile(
            db, entity_type, entity_id, owner_id,
            max_narratives=3, graph=graph,
        )

        logger.info("Generated profile for %s:%s", entity_type, entity_id)
        _update_job_progress(db, job_id, success=True)

    except Exception:
        logger.exception("Failed to generate profile for %s:%s", entity_type, entity_id)
        _update_job_progress(db, job_id, success=False)
```

**Step 4: Create the Lambda entry point**

The Lambda handler that receives SQS events and calls `handle_profile_generation_message`. This goes in the same file or a separate handler file, depending on how other workers are structured. Check existing workers (e.g., `backend/app/worker.py` or similar) and follow the same pattern.

The handler parses the SQS event, extracts the message body, creates a DB session, and calls `handle_profile_generation_message`.

**Step 5: Run tests, lint, commit**

```bash
poetry run python -m pytest tests/test_profile_worker.py -v
poetry run ruff check backend/app/services/profile_worker.py backend/tests/test_profile_worker.py
poetry run ruff format backend/app/services/profile_worker.py backend/tests/test_profile_worker.py
git add backend/app/services/profile_worker.py backend/tests/test_profile_worker.py
git commit -m "feat: add profile generation worker handler (#1550)"
```

---

## Task 7: Terraform module for profile worker (infrastructure)

**Files:**
- Create: `infra/terraform/modules/profile-worker/main.tf` (copy from `analysis-worker/main.tf`, rename resources)
- Create: `infra/terraform/modules/profile-worker/variables.tf` (copy from `analysis-worker/variables.tf`)
- Create: `infra/terraform/modules/profile-worker/outputs.tf` (copy from `analysis-worker/outputs.tf`)
- Modify: `infra/terraform/envs/staging.tfvars` (add module invocation)
- Modify: `infra/terraform/envs/prod.tfvars` (add module invocation)
- Modify: `infra/terraform/main.tf` (add module block + wire env var to API Lambda)

**Branch:** `feat/ep-wave3-infra` (separate from code branch)

**Step 1: Copy analysis-worker module and rename**

Copy the entire `modules/analysis-worker/` directory to `modules/profile-worker/`. Then in the new directory:

- `main.tf`: Replace all `analysis` references with `profile-generation`:
  - Queue name: `${var.name_prefix}-profile-generation-jobs`
  - DLQ name: `${var.name_prefix}-profile-generation-jobs-dlq`
  - Lambda name: `${var.name_prefix}-profile-worker`
  - IAM role: `${var.name_prefix}-profile-worker-exec-role`
  - Log group: `/aws/lambda/${var.name_prefix}-profile-worker`
  - Policy names: `sqs-send-profile-generation-jobs`

- `variables.tf`: Same structure, update default handler to `app.services.profile_worker.handler` (or whatever the Lambda entry point will be)

- `outputs.tf`: Same structure, update descriptions

**Step 2: Wire into main.tf**

Add module block in `infra/terraform/main.tf` (follow the pattern of the existing analysis-worker module invocation). Pass:
- `name_prefix`, `environment`, `s3_bucket`, `s3_key`
- VPC config: `subnet_ids`, `security_group_ids`
- `secrets_arns` (database secret)
- `bedrock_model_ids`
- `api_lambda_role_name` (for SQS send permission)
- `environment_variables` including: `BMX_DATABASE_SECRET_ARN`, `BMX_REDIS_URL`, `BMX_PROFILE_GENERATION_QUEUE_NAME`

Add the queue name env var to the main API Lambda's environment variables:
```hcl
BMX_PROFILE_GENERATION_QUEUE_NAME = module.profile_worker[0].queue_name
```

**Step 3: Validate**

```bash
cd infra/terraform
AWS_PROFILE=bmx-staging terraform validate
AWS_PROFILE=bmx-staging terraform plan -var-file=envs/staging.tfvars
```

**Step 4: Commit**

```bash
git add infra/terraform/modules/profile-worker/
git add infra/terraform/main.tf infra/terraform/envs/
git commit -m "feat: add Terraform module for profile generation worker (#1550)"
```

---

## Review and Merge Sequence

1. **PR B (infra):** Create PR `feat/ep-wave3-infra` -> staging. Review. Merge with squash. Apply with `terraform apply`.
2. **PR A (code):** Create PR `feat/ep-wave3` -> staging. Review (bmx-review-changes + apply-review-feedback). Merge with squash.
3. **Validate staging:** Health check + test profile generation endpoint.
4. **Close issues:** #1549, #1550
5. **Promote:** staging -> main

---

## Files Summary

| File | Action | Task |
|------|--------|------|
| `backend/app/services/social_circles_cache.py` | Modify | 1 |
| `backend/tests/test_social_circles_cache.py` | Create/Modify | 1 |
| `backend/app/services/entity_profile.py` | Modify | 2 |
| `backend/app/api/v1/entity_profile.py` | Modify | 2, 5 |
| `backend/tests/test_entity_profile.py` | Modify | 2, 5 |
| `backend/app/models/profile_generation_job.py` | Create | 3 |
| `backend/alembic/versions/<rev>_add_profile_generation_jobs.py` | Create | 3 |
| `backend/app/db/migration_sql.py` | Modify | 3 |
| `backend/app/config.py` | Modify | 4 |
| `backend/app/services/sqs.py` | Modify | 4 |
| `backend/tests/test_sqs.py` | Create/Modify | 4 |
| `backend/app/services/profile_worker.py` | Create | 6 |
| `backend/tests/test_profile_worker.py` | Create | 6 |
| `infra/terraform/modules/profile-worker/*` | Create | 7 |
| `infra/terraform/main.tf` | Modify | 7 |
| `infra/terraform/envs/*.tfvars` | Modify | 7 |
