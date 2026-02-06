#!/bin/bash
# safe-commit.sh - Enforces staging-first workflow
# Usage: ./scripts/safe-commit.sh "feat: your commit message"

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

current_branch=$(git symbolic-ref HEAD 2>/dev/null | sed 's|refs/heads/||')

echo ""
echo "============================================"
echo "  BlueMoxon Safe Commit Script"
echo "============================================"
echo ""

# Block if on main or staging
if [ "$current_branch" = "main" ] || [ "$current_branch" = "staging" ]; then
    echo -e "${RED}ERROR: You are on '$current_branch' branch!${NC}"
    echo ""
    echo "You MUST work on a feature branch. Run:"
    echo ""
    echo "  git checkout -b feat/your-feature-name"
    echo ""
    exit 1
fi

# Check for commit message
if [ -z "$1" ]; then
    echo -e "${RED}ERROR: Commit message required${NC}"
    echo ""
    echo "Usage: ./scripts/safe-commit.sh \"feat: your commit message\""
    echo ""
    exit 1
fi

commit_msg="$1"

# Validate conventional commit format
if ! echo "$commit_msg" | grep -qE "^(feat|fix|docs|style|refactor|perf|test|chore|ci|build|revert)(\(.+\))?: .+"; then
    echo -e "${YELLOW}WARNING: Commit message doesn't follow conventional format${NC}"
    echo "Expected: <type>: <description>"
    echo "Types: feat, fix, docs, style, refactor, perf, test, chore, ci, build, revert"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}Branch: $current_branch${NC}"
echo ""

# Run linters
echo "Running linters..."
cd "$(git rev-parse --show-toplevel)"

if [ -d "frontend" ]; then
    echo "  - Frontend lint..."
    npm run --prefix frontend lint --silent || true
    echo "  - Frontend format..."
    npm run --prefix frontend format --silent || true
fi

if [ -d "backend" ]; then
    echo "  - Backend lint..."
    poetry run ruff check backend/ --fix --silent 2>/dev/null || true
    echo "  - Backend format..."
    poetry run ruff format backend/ --silent 2>/dev/null || true
fi

# Stage and commit
echo ""
echo "Staging changes..."
git add -A

echo "Committing..."
git commit -m "$commit_msg

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"

echo ""
echo -e "${GREEN}Committed successfully!${NC}"
echo ""
echo "Next steps:"
echo "  1. git push -u origin $current_branch"
echo "  2. gh pr create --base staging --title \"$commit_msg\""
echo "  3. Wait for CI to pass"
echo "  4. Merge PR to staging"
echo "  5. Validate in https://staging.app.bluemoxon.com"
echo "  6. Create PR from staging to main"
echo ""
