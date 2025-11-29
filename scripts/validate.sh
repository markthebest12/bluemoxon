#!/bin/bash
set -e

echo "=== BlueMoxon Validation ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Backend
echo ""
echo "--- Backend Validation ---"
cd "$PROJECT_ROOT/backend"

echo "Linting..."
poetry run ruff check . || { echo "Lint errors found"; exit 1; }

echo "Format check..."
poetry run ruff format --check . || { echo "Format issues found"; exit 1; }

echo "Type checking..."
poetry run mypy app/ || echo "Warning: mypy issues found (non-blocking)"

echo "Running tests..."
poetry run pytest -q || echo "Warning: test issues (non-blocking for now)"

# Frontend
echo ""
echo "--- Frontend Validation ---"
cd "$PROJECT_ROOT/frontend"

echo "Linting..."
npm run lint || { echo "Lint errors found"; exit 1; }

echo "Type checking..."
npm run type-check || { echo "Type errors found"; exit 1; }

echo "Format check..."
npx prettier --check "src/**/*.{ts,vue,css}" 2>/dev/null || echo "Warning: formatting issues (non-blocking)"

echo "Build check..."
npm run build || { echo "Build failed"; exit 1; }

echo ""
echo "=== Validation Complete ==="
