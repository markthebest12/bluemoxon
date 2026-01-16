# Entity Reassignment API Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.
> **IMPORTANT:** Do NOT delete the worktree after completion - it will be reused for PR 3 (Frontend UI).

**Goal:** Add endpoints to reassign books from one entity to another before deletion, enabling duplicate entity merging.

**Architecture:** Each entity (Author, Publisher, Binder) gets a `/reassign` POST endpoint that moves all associated books to a target entity, then deletes the source entity. Uses SQLAlchemy bulk update for efficiency.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest

---

## Task 1: Add Reassignment Schemas

**Files:**

- Modify: `backend/app/schemas/reference.py`

**Step 1: Add schemas to reference.py**

Add at the end of `backend/app/schemas/reference.py`:

```python
# Reassignment schemas
class ReassignRequest(BaseModel):
    """Request schema for reassigning books to another entity."""

    target_id: int


class ReassignResponse(BaseModel):
    """Response schema for reassignment operation."""

    reassigned_count: int
    deleted_entity: str
    target_entity: str
```

**Step 2: Verify file is valid Python**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/608-reassignment-api/backend`
Run: `python -c "from app.schemas.reference import ReassignRequest, ReassignResponse; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add backend/app/schemas/reference.py
git commit -m "feat(schemas): add ReassignRequest and ReassignResponse for entity reassignment"
```

---

## Task 2: Author Reassignment - Failing Test

**Files:**

- Test: `backend/tests/api/v1/test_authors.py`

**Step 1: Write the failing tests**

Add to `backend/tests/api/v1/test_authors.py`:

```python
def test_reassign_author_moves_books_to_target(client, db):
    """Reassign endpoint moves all books from source to target author."""
    from app.models import Author, Book

    source = Author(name="Source Author")
    target = Author(name="Target Author")
    db.add_all([source, target])
    db.commit()
    db.refresh(source)
    db.refresh(target)

    book1 = Book(title="Book 1", author_id=source.id)
    book2 = Book(title="Book 2", author_id=source.id)
    db.add_all([book1, book2])
    db.commit()

    response = client.post(
        f"/api/v1/authors/{source.id}/reassign",
        json={"target_id": target.id},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["reassigned_count"] == 2
    assert data["deleted_entity"] == "Source Author"
    assert data["target_entity"] == "Target Author"

    assert db.query(Author).filter(Author.id == source.id).first() is None

    db.refresh(book1)
    db.refresh(book2)
    assert book1.author_id == target.id
    assert book2.author_id == target.id


def test_reassign_author_404_when_source_not_found(client, db):
    """Reassign returns 404 when source author doesn't exist."""
    from app.models import Author

    target = Author(name="Target Author")
    db.add(target)
    db.commit()
    db.refresh(target)

    response = client.post(
        "/api/v1/authors/99999/reassign",
        json={"target_id": target.id},
    )
    assert response.status_code == 404


def test_reassign_author_400_when_target_not_found(client, db):
    """Reassign returns 400 when target author doesn't exist."""
    from app.models import Author

    source = Author(name="Source Author")
    db.add(source)
    db.commit()
    db.refresh(source)

    response = client.post(
        f"/api/v1/authors/{source.id}/reassign",
        json={"target_id": 99999},
    )
    assert response.status_code == 400


def test_reassign_author_400_when_same_entity(client, db):
    """Reassign returns 400 when source and target are the same."""
    from app.models import Author

    author = Author(name="Same Author")
    db.add(author)
    db.commit()
    db.refresh(author)

    response = client.post(
        f"/api/v1/authors/{author.id}/reassign",
        json={"target_id": author.id},
    )
    assert response.status_code == 400
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/608-reassignment-api/backend`
Run: `poetry run pytest tests/api/v1/test_authors.py::test_reassign_author_moves_books_to_target -v`
Expected: FAIL with 404

**Step 3: Commit failing tests**

```bash
git add backend/tests/api/v1/test_authors.py
git commit -m "test(authors): add failing tests for author reassignment endpoint"
```

---

## Task 3: Author Reassignment - Implementation

**Files:**

- Modify: `backend/app/api/v1/authors.py`

**Step 1: Update imports**

Change import line to:

```python
from app.models import Author, Book
from app.schemas.reference import AuthorCreate, AuthorResponse, AuthorUpdate, ReassignRequest, ReassignResponse
```

**Step 2: Add endpoint at end of file**

```python
@router.post("/{author_id}/reassign", response_model=ReassignResponse)
def reassign_author_books(
    author_id: int,
    body: ReassignRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Reassign all books from source author to target author, then delete source."""
    source = db.query(Author).filter(Author.id == author_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source author not found")

    if author_id == body.target_id:
        raise HTTPException(status_code=400, detail="Cannot reassign to same author")

    target = db.query(Author).filter(Author.id == body.target_id).first()
    if not target:
        raise HTTPException(status_code=400, detail="Target author not found")

    book_count = db.query(Book).filter(Book.author_id == author_id).count()
    db.query(Book).filter(Book.author_id == author_id).update({"author_id": body.target_id})

    source_name = source.name
    target_name = target.name

    db.delete(source)
    db.commit()

    return ReassignResponse(
        reassigned_count=book_count,
        deleted_entity=source_name,
        target_entity=target_name,
    )
```

**Step 3: Run tests**

Run: `poetry run pytest tests/api/v1/test_authors.py -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add backend/app/api/v1/authors.py
git commit -m "feat(api): add author reassignment endpoint"
```

---

## Task 4: Publisher Reassignment - Failing Test

**Files:**

- Test: `backend/tests/api/v1/test_publishers.py`

**Step 1: Write the failing tests**

Add to `backend/tests/api/v1/test_publishers.py`:

```python
def test_reassign_publisher_moves_books_to_target(client, db):
    """Reassign endpoint moves all books from source to target publisher."""
    from app.models import Publisher, Book

    source = Publisher(name="Source Publisher")
    target = Publisher(name="Target Publisher")
    db.add_all([source, target])
    db.commit()
    db.refresh(source)
    db.refresh(target)

    book1 = Book(title="Book 1", publisher_id=source.id)
    book2 = Book(title="Book 2", publisher_id=source.id)
    db.add_all([book1, book2])
    db.commit()

    response = client.post(
        f"/api/v1/publishers/{source.id}/reassign",
        json={"target_id": target.id},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["reassigned_count"] == 2
    assert data["deleted_entity"] == "Source Publisher"
    assert data["target_entity"] == "Target Publisher"

    assert db.query(Publisher).filter(Publisher.id == source.id).first() is None

    db.refresh(book1)
    db.refresh(book2)
    assert book1.publisher_id == target.id
    assert book2.publisher_id == target.id


def test_reassign_publisher_404_when_source_not_found(client, db):
    """Reassign returns 404 when source publisher doesn't exist."""
    from app.models import Publisher

    target = Publisher(name="Target Publisher")
    db.add(target)
    db.commit()
    db.refresh(target)

    response = client.post(
        "/api/v1/publishers/99999/reassign",
        json={"target_id": target.id},
    )
    assert response.status_code == 404


def test_reassign_publisher_400_when_target_not_found(client, db):
    """Reassign returns 400 when target publisher doesn't exist."""
    from app.models import Publisher

    source = Publisher(name="Source Publisher")
    db.add(source)
    db.commit()
    db.refresh(source)

    response = client.post(
        f"/api/v1/publishers/{source.id}/reassign",
        json={"target_id": 99999},
    )
    assert response.status_code == 400


def test_reassign_publisher_400_when_same_entity(client, db):
    """Reassign returns 400 when source and target are the same."""
    from app.models import Publisher

    publisher = Publisher(name="Same Publisher")
    db.add(publisher)
    db.commit()
    db.refresh(publisher)

    response = client.post(
        f"/api/v1/publishers/{publisher.id}/reassign",
        json={"target_id": publisher.id},
    )
    assert response.status_code == 400
```

**Step 2: Run tests to verify they fail**

Run: `poetry run pytest tests/api/v1/test_publishers.py::test_reassign_publisher_moves_books_to_target -v`
Expected: FAIL with 404

**Step 3: Commit**

```bash
git add backend/tests/api/v1/test_publishers.py
git commit -m "test(publishers): add failing tests for publisher reassignment endpoint"
```

---

## Task 5: Publisher Reassignment - Implementation

**Files:**

- Modify: `backend/app/api/v1/publishers.py`

**Step 1: Update imports**

```python
from app.models import Publisher, Book
from app.schemas.reference import PublisherCreate, PublisherResponse, PublisherUpdate, ReassignRequest, ReassignResponse
```

**Step 2: Add endpoint at end of file**

```python
@router.post("/{publisher_id}/reassign", response_model=ReassignResponse)
def reassign_publisher_books(
    publisher_id: int,
    body: ReassignRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Reassign all books from source publisher to target publisher, then delete source."""
    source = db.query(Publisher).filter(Publisher.id == publisher_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source publisher not found")

    if publisher_id == body.target_id:
        raise HTTPException(status_code=400, detail="Cannot reassign to same publisher")

    target = db.query(Publisher).filter(Publisher.id == body.target_id).first()
    if not target:
        raise HTTPException(status_code=400, detail="Target publisher not found")

    book_count = db.query(Book).filter(Book.publisher_id == publisher_id).count()
    db.query(Book).filter(Book.publisher_id == publisher_id).update({"publisher_id": body.target_id})

    source_name = source.name
    target_name = target.name

    db.delete(source)
    db.commit()

    return ReassignResponse(
        reassigned_count=book_count,
        deleted_entity=source_name,
        target_entity=target_name,
    )
```

**Step 3: Run tests**

Run: `poetry run pytest tests/api/v1/test_publishers.py -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add backend/app/api/v1/publishers.py
git commit -m "feat(api): add publisher reassignment endpoint"
```

---

## Task 6: Binder Reassignment - Failing Test

**Files:**

- Test: `backend/tests/api/v1/test_binders.py`

**Step 1: Write the failing tests**

Add to `backend/tests/api/v1/test_binders.py`:

```python
def test_reassign_binder_moves_books_to_target(client, db):
    """Reassign endpoint moves all books from source to target binder."""
    from app.models import Binder, Book

    source = Binder(name="Source Binder")
    target = Binder(name="Target Binder")
    db.add_all([source, target])
    db.commit()
    db.refresh(source)
    db.refresh(target)

    book1 = Book(title="Book 1", binder_id=source.id)
    book2 = Book(title="Book 2", binder_id=source.id)
    db.add_all([book1, book2])
    db.commit()

    response = client.post(
        f"/api/v1/binders/{source.id}/reassign",
        json={"target_id": target.id},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["reassigned_count"] == 2
    assert data["deleted_entity"] == "Source Binder"
    assert data["target_entity"] == "Target Binder"

    assert db.query(Binder).filter(Binder.id == source.id).first() is None

    db.refresh(book1)
    db.refresh(book2)
    assert book1.binder_id == target.id
    assert book2.binder_id == target.id


def test_reassign_binder_404_when_source_not_found(client, db):
    """Reassign returns 404 when source binder doesn't exist."""
    from app.models import Binder

    target = Binder(name="Target Binder")
    db.add(target)
    db.commit()
    db.refresh(target)

    response = client.post(
        "/api/v1/binders/99999/reassign",
        json={"target_id": target.id},
    )
    assert response.status_code == 404


def test_reassign_binder_400_when_target_not_found(client, db):
    """Reassign returns 400 when target binder doesn't exist."""
    from app.models import Binder

    source = Binder(name="Source Binder")
    db.add(source)
    db.commit()
    db.refresh(source)

    response = client.post(
        f"/api/v1/binders/{source.id}/reassign",
        json={"target_id": 99999},
    )
    assert response.status_code == 400


def test_reassign_binder_400_when_same_entity(client, db):
    """Reassign returns 400 when source and target are the same."""
    from app.models import Binder

    binder = Binder(name="Same Binder")
    db.add(binder)
    db.commit()
    db.refresh(binder)

    response = client.post(
        f"/api/v1/binders/{binder.id}/reassign",
        json={"target_id": binder.id},
    )
    assert response.status_code == 400
```

**Step 2: Run tests to verify they fail**

Run: `poetry run pytest tests/api/v1/test_binders.py::test_reassign_binder_moves_books_to_target -v`
Expected: FAIL with 404

**Step 3: Commit**

```bash
git add backend/tests/api/v1/test_binders.py
git commit -m "test(binders): add failing tests for binder reassignment endpoint"
```

---

## Task 7: Binder Reassignment - Implementation

**Files:**

- Modify: `backend/app/api/v1/binders.py`

**Step 1: Update imports**

```python
from app.models import Binder, Book
from app.schemas.reference import BinderCreate, BinderResponse, BinderUpdate, ReassignRequest, ReassignResponse
```

**Step 2: Add endpoint at end of file**

```python
@router.post("/{binder_id}/reassign", response_model=ReassignResponse)
def reassign_binder_books(
    binder_id: int,
    body: ReassignRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Reassign all books from source binder to target binder, then delete source."""
    source = db.query(Binder).filter(Binder.id == binder_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source binder not found")

    if binder_id == body.target_id:
        raise HTTPException(status_code=400, detail="Cannot reassign to same binder")

    target = db.query(Binder).filter(Binder.id == body.target_id).first()
    if not target:
        raise HTTPException(status_code=400, detail="Target binder not found")

    book_count = db.query(Book).filter(Book.binder_id == binder_id).count()
    db.query(Book).filter(Book.binder_id == binder_id).update({"binder_id": body.target_id})

    source_name = source.name
    target_name = target.name

    db.delete(source)
    db.commit()

    return ReassignResponse(
        reassigned_count=book_count,
        deleted_entity=source_name,
        target_entity=target_name,
    )
```

**Step 3: Run tests**

Run: `poetry run pytest tests/api/v1/test_binders.py -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add backend/app/api/v1/binders.py
git commit -m "feat(api): add binder reassignment endpoint"
```

---

## Task 8: Final Validation

**Step 1: Run all tests**

Run: `poetry run pytest -q`
Expected: All tests PASS

**Step 2: Run linter**

Run: `poetry run ruff check .`
Expected: No errors

**Step 3: Format check**

Run: `poetry run ruff format --check .`
Expected: All OK (or run `poetry run ruff format .` to fix)

---

## Task 9: Push and Create PR

**Step 1: Push to origin**

Run: `git push -u origin feat/608-entity-reassignment`

**Step 2: Create PR**

Run: `gh pr create --base staging --title "feat: Add entity reassignment endpoints (#608)" --body "..."`

---

## Summary

3 reassignment endpoints with full TDD:

- `POST /api/v1/authors/{id}/reassign`
- `POST /api/v1/publishers/{id}/reassign`
- `POST /api/v1/binders/{id}/reassign`

Total: 12 new tests (4 per entity type)

**REMINDER:** Do NOT delete the worktree - it will be reused for PR 3 (Frontend UI).
