#!/usr/bin/env bash
# Shared retry functions for deploy smoke tests.
# Source this file at the top of each smoke test step:
#   source "$GITHUB_WORKSPACE/.github/scripts/smoke-helpers.sh"

retry_curl() {
  local url="$1"; local desc="$2"; local max="${3:-5}"; local delay="${4:-3}"
  shift 4 2>/dev/null || shift $#
  for attempt in $(seq 1 "$max"); do
    echo "Attempt $attempt/$max: $desc" >&2
    response=$(curl -s -w "\n%{http_code}" "$@" "$url")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
      echo "✓ $desc succeeded (HTTP $http_code)" >&2
      echo "$body"
      return 0
    fi
    echo "✗ $desc failed (HTTP $http_code), retrying in ${delay}s..." >&2
    sleep "$delay"
  done
  echo "::error::$desc failed after $max attempts" >&2
  return 1
}

retry_head() {
  local url="$1"; local desc="$2"; local max="${3:-5}"; local delay="${4:-3}"
  shift 4 2>/dev/null || shift $#
  for attempt in $(seq 1 "$max"); do
    echo "Attempt $attempt/$max: $desc" >&2
    http_code=$(curl -sI -L -o /dev/null -w "%{http_code}" "$@" "$url")
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 400 ]; then
      echo "✓ $desc succeeded (HTTP $http_code)" >&2
      return 0
    fi
    echo "✗ $desc failed (HTTP $http_code), retrying in ${delay}s..." >&2
    sleep "$delay"
  done
  echo "::error::$desc failed after $max attempts" >&2
  return 1
}
