# Local Development Guide

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- AWS CLI (configured with credentials)
- Poetry (Python dependency management)

## Initial Setup

### Clone Repository

```bash
git clone <repo-url>
cd bluemoxon
```

### Backend Setup

```bash
cd backend

# Install dependencies
poetry install

# Copy environment template
cp .env.example .env

# Edit .env with local settings
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment template
cp .env.example .env.local
```

### Local Database (Docker)

```bash
# Start PostgreSQL
docker-compose up -d postgres

# Run migrations
cd backend
alembic upgrade head

# Seed reference data
python scripts/seed_data.py
```

## Running Locally

### Backend (Terminal 1)

```bash
cd backend
poetry run uvicorn app.main:app --reload --port 8000
```

API available at: <http://localhost:8000>
Docs available at: <http://localhost:8000/docs>

### Frontend (Terminal 2)

```bash
cd frontend
npm run dev
```

App available at: <http://localhost:5173>

## Environment Variables

### Backend (.env)

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bluemoxon
AWS_REGION=us-east-1
COGNITO_USER_POOL_ID=<local-or-dev-pool>
COGNITO_APP_CLIENT_ID=<client-id>
S3_IMAGES_BUCKET=bluemoxon-images-dev
CORS_ORIGINS=http://localhost:5173
```

### Frontend (.env.local)

```bash
VITE_API_URL=http://localhost:8000/api/v1
VITE_COGNITO_USER_POOL_ID=<pool-id>
VITE_COGNITO_APP_CLIENT_ID=<client-id>
VITE_COGNITO_REGION=us-east-1
```

## Testing

### Backend Tests

```bash
cd backend
poetry run pytest
poetry run pytest --cov=app  # with coverage
```

### Frontend Tests

```bash
cd frontend
npm run test
npm run test:coverage
```

## Code Quality

### Pre-commit Hooks (Recommended)

Install pre-commit hooks to catch issues before CI:

```bash
# One-time setup
pip install pre-commit
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

**Hooks configured:**

| Hook | Purpose |
|------|---------|
| Ruff | Python linting + formatting |
| ESLint | TypeScript/Vue linting |
| Prettier | Frontend formatting |
| Mypy | Python type checking |

### Backend

```bash
cd backend
poetry run ruff format .     # Format
poetry run ruff check .      # Lint
poetry run mypy .            # Type check
```

### Frontend

```bash
cd frontend
npm run lint                 # ESLint
npm run format               # Prettier (REQUIRED before commit)
npm run type-check           # TypeScript
```

### Strict TypeScript Rules

ESLint is configured with strict rules (#808):

- `@typescript-eslint/no-explicit-any` - Warns on `any` usage
- `@typescript-eslint/explicit-function-return-types` - Requires return types
- Type-safe Vue component props

## Docker Compose (Full Stack)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all
docker-compose down
```

## Useful Commands

```bash
# Create new migration
cd backend
alembic revision --autogenerate -m "Add new field"

# Reset database
docker-compose down -v
docker-compose up -d postgres
alembic upgrade head

# Import legacy data
python scripts/sync_from_legacy.py --source ~/projects/book-collection --apply
```
