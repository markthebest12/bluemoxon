# BlueMoxon Validation & CI/CD Blueprint

This document defines validation steps for the CI/CD pipeline, covering syntax checking, integration testing, and code formatting.

## Overview

| Stage | Backend (Python) | Frontend (TypeScript) |
|-------|------------------|----------------------|
| Syntax/Lint | ruff, mypy | eslint, vue-tsc |
| Format | ruff format, black | prettier |
| Unit Tests | pytest | vitest |
| Integration | pytest + testcontainers | playwright (future) |
| Build | - | vite build |

---

## 1. Backend Validation (Python/FastAPI)

### 1.1 Syntax & Linting

**Tool:** [Ruff](https://github.com/astral-sh/ruff) - Fast Python linter

```bash
cd backend

# Install (if not in pyproject.toml)
poetry add --group dev ruff

# Run linter
poetry run ruff check .

# Auto-fix issues
poetry run ruff check --fix .
```

**Configuration** (`pyproject.toml`):

```toml
[tool.ruff]
target-version = "py311"
line-length = 100
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # Pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
]
ignore = [
    "E501",   # line too long (handled by formatter)
]

[tool.ruff.isort]
known-first-party = ["app"]
```

### 1.2 Type Checking

**Tool:** [mypy](https://mypy-lang.org/) - Static type checker

```bash
# Install
poetry add --group dev mypy

# Run type checker
poetry run mypy app/
```

**Configuration** (`pyproject.toml`):

```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = true
plugins = ["sqlalchemy.ext.mypy.plugin"]

[[tool.mypy.overrides]]
module = "mangum.*"
ignore_missing_imports = true
```

### 1.3 Code Formatting

**Tool:** Ruff formatter (or Black)

```bash
# Check formatting
poetry run ruff format --check .

# Apply formatting
poetry run ruff format .
```

### 1.4 Unit Tests

**Tool:** [pytest](https://pytest.org/)

```bash
# Install
poetry add --group dev pytest pytest-asyncio pytest-cov httpx

# Run tests
poetry run pytest

# With coverage
poetry run pytest --cov=app --cov-report=html
```

**Configuration** (`pyproject.toml`):

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-v --tb=short"
```

**Sample Test Structure:**

```text
backend/tests/
├── conftest.py          # Fixtures (test DB, client)
├── test_books.py        # Book API tests
├── test_authors.py      # Author API tests
├── test_stats.py        # Statistics tests
└── test_export.py       # Export tests
```

**Sample Test** (`tests/conftest.py`):

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db import get_db
from app.models.base import Base

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

**Sample Test** (`tests/test_books.py`):

```python
def test_list_books_empty(client):
    response = client.get("/api/v1/books")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []

def test_create_book(client):
    response = client.post("/api/v1/books", json={
        "title": "Idylls of the King",
        "volumes": 1,
        "inventory_type": "PRIMARY",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Idylls of the King"
    assert data["id"] is not None

def test_get_book_not_found(client):
    response = client.get("/api/v1/books/999")
    assert response.status_code == 404
```

### 1.5 Integration Tests

**Tool:** pytest + testcontainers (for PostgreSQL)

```bash
poetry add --group dev testcontainers
```

**Sample** (`tests/integration/conftest.py`):

```python
import pytest
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:15") as postgres:
        yield postgres

@pytest.fixture(scope="function")
def db_url(postgres_container):
    return postgres_container.get_connection_url()
```

---

## 2. Frontend Validation (Vue/TypeScript)

### 2.1 Syntax & Linting

**Tool:** [ESLint](https://eslint.org/) with Vue plugin

```bash
cd frontend

# Install (typically included in Vue project)
npm install -D eslint @vue/eslint-config-typescript

# Run linter
npm run lint

# Auto-fix
npm run lint -- --fix
```

**Configuration** (`.eslintrc.cjs`):

```javascript
module.exports = {
  root: true,
  env: {
    browser: true,
    es2021: true,
    node: true,
  },
  extends: [
    'plugin:vue/vue3-recommended',
    'eslint:recommended',
    '@vue/eslint-config-typescript',
  ],
  parserOptions: {
    ecmaVersion: 'latest',
  },
  rules: {
    'vue/multi-word-component-names': 'off',
    '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
  },
}
```

### 2.2 Type Checking

**Tool:** [vue-tsc](https://github.com/vuejs/language-tools) - Vue TypeScript compiler

```bash
# Run type check
npm run type-check

# Or directly
npx vue-tsc --noEmit
```

**Script** (`package.json`):

```json
{
  "scripts": {
    "type-check": "vue-tsc --noEmit"
  }
}
```

### 2.3 Code Formatting

**Tool:** [Prettier](https://prettier.io/)

```bash
# Install
npm install -D prettier @vue/eslint-config-prettier

# Check formatting
npx prettier --check "src/**/*.{ts,vue,css}"

# Apply formatting
npx prettier --write "src/**/*.{ts,vue,css}"
```

**Configuration** (`.prettierrc`):

```json
{
  "semi": false,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100,
  "vueIndentScriptAndStyle": false
}
```

### 2.4 Unit Tests

**Tool:** [Vitest](https://vitest.dev/) - Vite-native testing

```bash
# Install
npm install -D vitest @vue/test-utils happy-dom

# Run tests
npm run test

# With coverage
npm run test:coverage
```

**Configuration** (`vite.config.ts`):

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: 'happy-dom',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
    },
  },
})
```

**Scripts** (`package.json`):

```json
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage"
  }
}
```

**Sample Test** (`src/stores/__tests__/books.test.ts`):

```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useBooksStore } from '../books'

describe('Books Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('initializes with empty books', () => {
    const store = useBooksStore()
    expect(store.books).toEqual([])
    expect(store.loading).toBe(false)
  })
})
```

### 2.5 Build Validation

```bash
# Production build (catches any build errors)
npm run build

# Preview build
npm run preview
```

---

## 3. CI/CD Pipeline Stages

### 3.1 Pipeline Overview

```yaml
stages:
  - validate
  - test
  - build
  - deploy
```

### 3.2 Validate Stage

```yaml
# Backend validation
backend-lint:
  stage: validate
  script:
    - cd backend
    - poetry install
    - poetry run ruff check .
    - poetry run ruff format --check .
    - poetry run mypy app/

# Frontend validation
frontend-lint:
  stage: validate
  script:
    - cd frontend
    - npm ci
    - npm run lint
    - npm run type-check
    - npx prettier --check "src/**/*.{ts,vue,css}"
```

### 3.3 Test Stage

```yaml
# Backend tests
backend-test:
  stage: test
  services:
    - postgres:15
  script:
    - cd backend
    - poetry install
    - poetry run pytest --cov=app --cov-report=xml
  coverage: '/TOTAL.*\s+(\d+%)/'

# Frontend tests
frontend-test:
  stage: test
  script:
    - cd frontend
    - npm ci
    - npm run test:coverage
```

### 3.4 Build Stage

```yaml
# Backend (container)
backend-build:
  stage: build
  script:
    - docker build -t bluemoxon-api ./backend

# Frontend (static)
frontend-build:
  stage: build
  script:
    - cd frontend
    - npm ci
    - npm run build
  artifacts:
    paths:
      - frontend/dist/
```

---

## 4. Local Validation Script

Create a script to run all validations locally before pushing:

**`scripts/validate.sh`:**

```bash
#!/bin/bash
set -e

echo "=== BlueMoxon Validation ==="

# Backend
echo ""
echo "--- Backend Validation ---"
cd backend

echo "Linting..."
poetry run ruff check .

echo "Format check..."
poetry run ruff format --check .

echo "Type checking..."
poetry run mypy app/ || echo "Warning: mypy issues found"

echo "Running tests..."
poetry run pytest -q

cd ..

# Frontend
echo ""
echo "--- Frontend Validation ---"
cd frontend

echo "Linting..."
npm run lint

echo "Type checking..."
npm run type-check

echo "Format check..."
npx prettier --check "src/**/*.{ts,vue,css}" || echo "Warning: formatting issues"

echo "Running tests..."
npm run test || echo "Warning: no tests yet"

echo "Build check..."
npm run build

cd ..

echo ""
echo "=== Validation Complete ==="
```

---

## 5. Current Validation Status

### Backend

| Check | Status | Notes |
|-------|--------|-------|
| Ruff linting | ✅ Configured | `poetry run ruff check .` |
| Mypy type checking | ✅ Configured | `poetry run mypy app/` |
| Ruff formatting | ✅ Configured | `poetry run ruff format --check .` |
| Pytest tests | ✅ 38 tests | Books, Stats, Health, Images, Analysis |
| Integration tests | ⚠️ Future | Add testcontainers for PostgreSQL |

### Frontend

| Check | Status | Notes |
|-------|--------|-------|
| ESLint | ✅ Available | `npm run lint` |
| vue-tsc | ✅ Available | `npm run type-check` |
| Prettier | ⚠️ Not configured | Add .prettierrc |
| Vitest | ⚠️ Not configured | Add to vite.config.ts |
| Build | ✅ Works | `npm run build` |

---

## 6. Next Steps

1. **Backend (Completed):**
   - [x] Add ruff, mypy, pytest to pyproject.toml dev dependencies
   - [x] Create ruff/mypy configuration in pyproject.toml
   - [x] Create tests/ directory with conftest.py
   - [x] Write initial API tests (20 tests for books, stats, health)

2. **Frontend Setup:**
   - [x] Verify ESLint configuration
   - [ ] Add Prettier configuration (.prettierrc)
   - [ ] Configure Vitest in vite.config.ts
   - [ ] Write initial store/component tests

3. **CI/CD:**
   - [ ] Create CodeBuild buildspec for validation
   - [ ] Add validation stage to pipeline
   - [ ] Configure test reporting

---

## 7. Commands Reference

### Quick Validation Commands

```bash
# Backend - all checks
cd backend && poetry run ruff check . && poetry run ruff format --check . && poetry run pytest

# Frontend - all checks
cd frontend && npm run lint && npm run type-check && npm run build

# Full validation script
./scripts/validate.sh
```

### Fix Commands

```bash
# Backend - auto-fix
cd backend && poetry run ruff check --fix . && poetry run ruff format .

# Frontend - auto-fix
cd frontend && npm run lint -- --fix && npx prettier --write "src/**/*.{ts,vue,css}"
```
