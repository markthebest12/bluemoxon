#!/bin/bash
# Validate and push changes - runs all checks locally before creating PR
# Usage: ./scripts/validate-and-push.sh "commit message"

set -e

COMMIT_MSG="${1:-update}"

echo "=== Pre-Push Validation ==="
echo ""

# Run backend checks
echo "[1/4] Backend lint check..."
cd backend
poetry run ruff check . || { echo "Backend lint failed!"; exit 1; }
poetry run ruff format --check . || { echo "Backend format failed! Run: poetry run ruff format ."; exit 1; }
cd ..

# Run frontend checks
echo "[2/4] Frontend lint check..."
cd frontend
npm run lint 2>/dev/null || { echo "Frontend lint failed!"; exit 1; }
npm run type-check 2>/dev/null || { echo "Frontend type-check failed!"; exit 1; }
cd ..

echo ""
echo "[3/4] All local checks passed!"
echo ""

# Get current branch
BRANCH=$(git branch --show-current)
if [ "$BRANCH" == "main" ]; then
  echo "ERROR: Cannot push directly to main!"
  echo "Create a feature branch first: git checkout -b <type>/<description>"
  exit 1
fi

# Commit and push
echo "[4/4] Committing and pushing..."
git add -A
git commit -m "$COMMIT_MSG" || echo "Nothing to commit"
git push -u origin "$BRANCH"

# Create PR
echo ""
echo "Creating PR..."
PR_URL=$(gh pr create --title "$COMMIT_MSG" --body "## Summary
- $COMMIT_MSG

## Test Plan
- [x] Local validation passed
- [ ] CI pipeline passes" 2>&1)

echo ""
echo "PR Created: $PR_URL"
echo ""
echo "Waiting for CI checks..."
PR_NUM=$(echo "$PR_URL" | grep -oE '[0-9]+$')
gh pr checks "$PR_NUM" --watch

echo ""
echo "CI passed! Merging..."
gh pr merge "$PR_NUM" --squash --delete-branch

echo ""
echo "=== Done! Changes merged to main ==="
