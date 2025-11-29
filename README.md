# BlueMoxon

Victorian Book Collection Management Web Application

**Name Origin:** Papa Smurf (Blue) + Edward Moxon (Victorian publisher of Tennyson)

## Overview

BlueMoxon is a web application for managing a Victorian book collection with:
- Browse and search across inventory with full-text search
- Detailed book analysis documents with markdown rendering
- Image gallery for book photos
- CSV and PDF export capabilities
- Role-based access control with 2FA

## Tech Stack

- **Frontend:** Vue 3 + Vite + TypeScript + TailwindCSS
- **Backend:** Python FastAPI + SQLAlchemy + Alembic
- **Database:** PostgreSQL (Aurora Serverless v2)
- **Auth:** AWS Cognito with MFA
- **Infrastructure:** AWS CDK (Python)
- **CI/CD:** AWS CodePipeline + CodeBuild

## Project Structure

```
bluemoxon/
├── frontend/          # Vue 3 SPA
├── backend/           # FastAPI application
├── infra/             # AWS CDK infrastructure
├── scripts/           # Migration and utility scripts
├── buildspec/         # CodeBuild specifications
└── docs/              # Documentation
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker
- Poetry (`curl -sSL https://install.python-poetry.org | python3 -`)

### Local Development

**One-command setup** (if using profile-scripts):
```bash
source ~/.zshrc
bmx-setup
```

**Manual setup:**
```bash
# Start PostgreSQL
docker-compose up -d postgres

# Backend (Terminal 1)
cd backend
cp .env.example .env
poetry install
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload

# Frontend (Terminal 2)
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

### Shell Aliases (via profile-scripts)

| Alias | Description |
|-------|-------------|
| `bmx` | cd to bluemoxon |
| `bmx-api` | Start backend server |
| `bmx-web` | Start frontend server |
| `bmx-db-start` | Start PostgreSQL container |
| `bmx-db-stop` | Stop PostgreSQL container |
| `bmx-db-psql` | Connect to database |
| `bmx-migrate` | Run Alembic migrations |

### Local URLs
- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

### Infrastructure Deployment

```bash
cd infra
poetry install
cdk bootstrap
cdk deploy --all
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - System design and decisions
- [API](docs/API.md) - API endpoint documentation
- [Database](docs/DATABASE.md) - Schema and migrations
- [Deployment](docs/DEPLOYMENT.md) - AWS setup guide
- [Development](docs/DEVELOPMENT.md) - Local dev setup
- [Migration](docs/MIGRATION.md) - Data migration from legacy system

## License

Private - All rights reserved
