#!/bin/bash
# PR Workflow Helper - Automates the gitflow process
# Usage: ./scripts/pr-workflow.sh <branch-type> <description>
# Example: ./scripts/pr-workflow.sh fix "remove unused import"

set -e

TYPE="${1:-feat}"
DESC="${2:-update}"
BRANCH_NAME="${TYPE}/${DESC// /-}"

echo "=== BlueMoxon PR Workflow ==="
echo "Branch: $BRANCH_NAME"
echo ""

# Step 1: Create branch
echo "[1/6] Creating branch..."
git checkout main
git pull origin main
git checkout -b "$BRANCH_NAME"

echo ""
echo "[2/6] Make your changes now, then run:"
echo "  ./scripts/pr-workflow.sh --continue"
echo ""
echo "Or to run the full flow at once:"
echo "  ./scripts/pr-workflow.sh --push \"$BRANCH_NAME\""
