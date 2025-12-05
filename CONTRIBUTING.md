# Contributing to BlueMoxon

Thank you for your interest in contributing to BlueMoxon!

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- Poetry (`curl -sSL https://install.python-poetry.org | python3 -`)

### Local Setup

```bash
# Clone the repository
git clone https://github.com/markthebest12/bluemoxon.git
cd bluemoxon

# Backend setup
cd backend
poetry install
poetry run pytest  # Verify tests pass

# Frontend setup
cd ../frontend
npm install
npm run type-check && npm run lint
```

## Development Workflow

1. **Create a branch:** `git checkout -b feat/my-feature`
2. **Make changes** and write tests
3. **Run validation:**
   ```bash
   cd backend && poetry run ruff check . && poetry run ruff format --check .
   cd frontend && npm run lint && npm run type-check
   ```
4. **Commit:** `git commit -m "feat: add my feature"`
5. **Open a PR:** `gh pr create`

### Branch Naming

- `feat/` - New features
- `fix/` - Bug fixes
- `refactor/` - Code refactoring
- `docs/` - Documentation
- `chore/` - Maintenance

### Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/):
- `feat: add book search filtering`
- `fix: resolve image upload timeout`
- `docs: update API reference`

## Pull Request Guidelines

- PRs require 1 approval before merging
- All CI checks must pass
- Keep PRs focused on a single change
- Use squash merge

## Code Style

- **Python:** Ruff formatting, type hints required
- **TypeScript:** ESLint + Prettier, Vue 3 Composition API

## Questions?

Open an issue or start a discussion.
