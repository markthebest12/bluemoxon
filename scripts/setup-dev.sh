#!/bin/bash
# Setup development environment with pre-commit hooks
# Run once after cloning: ./scripts/setup-dev.sh

set -e

echo "=== BlueMoxon Development Setup ==="

# Check prerequisites
command -v python3 >/dev/null 2>&1 || { echo "Python3 required"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Node.js required"; exit 1; }
command -v poetry >/dev/null 2>&1 || { echo "Poetry required"; exit 1; }

# Install pre-commit
echo "Installing pre-commit..."
pip install pre-commit --quiet

# Install pre-commit hooks
echo "Installing git hooks..."
pre-commit install

# Backend setup
echo "Setting up backend..."
cd backend
poetry install --quiet

# Frontend setup
echo "Setting up frontend..."
cd ../frontend
npm install --silent

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Pre-commit hooks installed. They will run automatically on commit:"
echo "  - ruff check (Python lint + auto-fix)"
echo "  - ruff format (Python formatting)"
echo "  - ESLint (Frontend lint)"
echo "  - TypeScript check"
echo ""
echo "To run hooks manually: pre-commit run --all-files"
echo ""
