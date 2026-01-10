# Dashboard Caching Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Redis-based caching to `/api/v1/stats/dashboard` endpoint with 5-minute TTL.

**Architecture:** ElastiCache Serverless (Redis) in VPC, Lambda connects via VPC config. Cache key is static `dashboard:stats:{params}`, TTL-only invalidation.

**Tech Stack:** AWS ElastiCache Serverless, redis-py, Terraform

---

## Task 1: Add Redis Dependency

**Files:**
- Modify: `backend/pyproject.toml`

**Step 1: Add redis to dependencies**

In `backend/pyproject.toml`, add redis to the dependencies section:

```toml
redis = "^5.0"
```

**Step 2: Install dependencies**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/perf-1002-dashboard-caching/backend && poetry add redis`

Expected: Poetry resolves and installs redis package.

**Step 3: Commit**

```bash
git add backend/pyproject.toml backend/poetry.lock
git commit -m "chore: Add redis dependency for dashboard caching"
```

---

## Task 2: Add redis_url to Settings

**Files:**
- Modify: `backend/app/config.py`
- Test: `backend/tests/test_config.py` (if exists, otherwise skip)

**Step 1: Add redis_url field to Settings class**

In `backend/app/config.py`, add after line ~118 (after api_key_hash):

```python
    # Redis cache
    redis_url: str = Field(
        default="",
        description="Redis URL for caching (empty = caching disabled)",
        validation_alias=AliasChoices("BMX_REDIS_URL", "REDIS_URL"),
    )
```

**Step 2: Verify config loads**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/perf-1002-dashboard-caching/backend && poetry run python -c "from app.config import get_settings; s = get_settings(); print(f'redis_url: {s.redis_url!r}')"`

Expected: `redis_url: ''`

**Step 3: Commit**

```bash
git add backend/app/config.py
git commit -m "feat: Add redis_url config setting"
```

---

## Task 3: Write Cache Module Tests (TDD)

**Files:**
- Create: `backend/tests/test_cache.py`

**Step 1: Write failing tests**

Create `backend/tests/test_cache.py`:

```python
"""Tests for cache module."""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestCachedDecorator:
    """Tests for the @cached decorator."""

    def test_cache_miss_calls_function_and_stores_result(self):
        """On cache miss, function is called and result is stored."""
        from app.cache import cached

        mock_redis = MagicMock()
        mock_redis.get.return_value = None  # Cache miss

        with patch("app.cache.get_redis", return_value=mock_redis):

            @cached(key="test:key", ttl=300)
            def my_func():
                return {"data": "value"}

            result = my_func()

        assert result == {"data": "value"}
        mock_redis.get.assert_called_once_with("test:key")
        mock_redis.setex.assert_called_once()
        # Verify TTL and serialized value
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "test:key"
        assert call_args[0][1] == 300
        assert json.loads(call_args[0][2]) == {"data": "value"}

    def test_cache_hit_returns_cached_value(self):
        """On cache hit, cached value is returned without calling function."""
        from app.cache import cached

        mock_redis = MagicMock()
        mock_redis.get.return_value = '{"cached": true}'  # Cache hit

        call_count = 0

        with patch("app.cache.get_redis", return_value=mock_redis):

            @cached(key="test:key", ttl=300)
            def my_func():
                nonlocal call_count
                call_count += 1
                return {"cached": False}

            result = my_func()

        assert result == {"cached": True}
        assert call_count == 0  # Function was NOT called
        mock_redis.setex.assert_not_called()

    def test_graceful_degradation_when_redis_unavailable(self):
        """Function works normally when Redis is not available."""
        from app.cache import cached

        with patch("app.cache.get_redis", return_value=None):

            @cached(key="test:key", ttl=300)
            def my_func():
                return {"data": "value"}

            result = my_func()

        assert result == {"data": "value"}

    def test_graceful_degradation_on_redis_get_error(self):
        """Function works normally when Redis GET fails."""
        from app.cache import cached

        mock_redis = MagicMock()
        mock_redis.get.side_effect = Exception("Connection failed")

        with patch("app.cache.get_redis", return_value=mock_redis):

            @cached(key="test:key", ttl=300)
            def my_func():
                return {"data": "value"}

            result = my_func()

        assert result == {"data": "value"}

    def test_graceful_degradation_on_redis_set_error(self):
        """Function works normally when Redis SET fails."""
        from app.cache import cached

        mock_redis = MagicMock()
        mock_redis.get.return_value = None  # Cache miss
        mock_redis.setex.side_effect = Exception("Connection failed")

        with patch("app.cache.get_redis", return_value=mock_redis):

            @cached(key="test:key", ttl=300)
            def my_func():
                return {"data": "value"}

            result = my_func()

        # Should still return result despite SET failing
        assert result == {"data": "value"}


class TestGetRedis:
    """Tests for get_redis function."""

    def test_returns_none_when_redis_url_empty(self):
        """Returns None when REDIS_URL is not configured."""
        from app.cache import _reset_client, get_redis

        _reset_client()  # Reset singleton

        with patch("app.cache.get_settings") as mock_settings:
            mock_settings.return_value.redis_url = ""
            client = get_redis()

        assert client is None

    def test_returns_client_when_redis_url_configured(self):
        """Returns Redis client when REDIS_URL is configured."""
        from app.cache import _reset_client, get_redis

        _reset_client()  # Reset singleton

        with patch("app.cache.get_settings") as mock_settings:
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            with patch("app.cache.redis.from_url") as mock_from_url:
                mock_client = MagicMock()
                mock_from_url.return_value = mock_client

                client = get_redis()

        assert client == mock_client
        mock_from_url.assert_called_once()

    def test_caches_client_instance(self):
        """Client instance is cached (singleton pattern)."""
        from app.cache import _reset_client, get_redis

        _reset_client()

        with patch("app.cache.get_settings") as mock_settings:
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            with patch("app.cache.redis.from_url") as mock_from_url:
                mock_client = MagicMock()
                mock_from_url.return_value = mock_client

                client1 = get_redis()
                client2 = get_redis()

        # from_url only called once
        assert mock_from_url.call_count == 1
        assert client1 is client2
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/perf-1002-dashboard-caching/backend && poetry run pytest tests/test_cache.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'app.cache'"

**Step 3: Commit failing tests**

```bash
git add backend/tests/test_cache.py
git commit -m "test: Add cache module tests (TDD - failing)"
```

---

## Task 4: Implement Cache Module

**Files:**
- Create: `backend/app/cache.py`

**Step 1: Create cache module**

Create `backend/app/cache.py`:

```python
"""Redis caching utilities for dashboard stats.

Provides a simple caching decorator with graceful degradation.
When Redis is unavailable, functions execute normally without caching.
"""

import json
import logging
from functools import wraps
from typing import Any, Callable, Optional

import redis

from app.config import get_settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None


def _reset_client() -> None:
    """Reset the cached client (for testing)."""
    global _redis_client
    _redis_client = None


def get_redis() -> Optional[redis.Redis]:
    """Get Redis client, or None if not configured.

    Returns:
        Redis client instance, or None if REDIS_URL is empty.
        Client is cached as a singleton.
    """
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        if settings.redis_url:
            try:
                _redis_client = redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
                logger.info("Redis client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis client: {e}")
    return _redis_client


def cached(key: str, ttl: int = 300) -> Callable:
    """Cache decorator with TTL and graceful degradation.

    Args:
        key: Redis key for caching
        ttl: Time-to-live in seconds (default 5 minutes)

    Returns:
        Decorator that caches function results.

    Example:
        @cached(key="dashboard:stats", ttl=300)
        def get_expensive_data():
            return {"data": "value"}
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            client = get_redis()

            # Try cache hit
            if client:
                try:
                    cached_value = client.get(key)
                    if cached_value:
                        logger.debug(f"Cache HIT: {key}")
                        return json.loads(cached_value)
                except Exception as e:
                    logger.warning(f"Redis GET failed for {key}: {e}")

            # Cache miss - execute function
            logger.debug(f"Cache MISS: {key}")
            result = func(*args, **kwargs)

            # Store in cache
            if client and result is not None:
                try:
                    serialized = json.dumps(result, default=str)
                    client.setex(key, ttl, serialized)
                    logger.debug(f"Cached {key} with TTL {ttl}s")
                except Exception as e:
                    logger.warning(f"Redis SETEX failed for {key}: {e}")

            return result

        return wrapper

    return decorator
```

**Step 2: Run tests to verify they pass**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/perf-1002-dashboard-caching/backend && poetry run pytest tests/test_cache.py -v`

Expected: PASS (all 8 tests)

**Step 3: Commit implementation**

```bash
git add backend/app/cache.py
git commit -m "feat: Implement cache module with graceful degradation"
```

---

## Task 5: Write Dashboard Caching Tests (TDD)

**Files:**
- Modify: `backend/tests/test_stats.py`

**Step 1: Add caching integration tests**

Add to end of `backend/tests/test_stats.py`:

```python
class TestDashboardCaching:
    """Tests for dashboard endpoint caching behavior."""

    def test_dashboard_returns_cached_response_on_hit(self, client):
        """Dashboard returns cached data when available."""
        from unittest.mock import MagicMock, patch

        cached_response = {
            "overview": {"primary": {"count": 99}},
            "bindings": [],
            "by_era": [],
            "by_publisher": [],
            "by_author": [],
            "acquisitions_daily": [],
            "by_condition": [],
            "by_category": [],
        }

        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps(cached_response)

        with patch("app.services.dashboard_stats.get_redis", return_value=mock_redis):
            response = client.get("/api/v1/stats/dashboard")

        assert response.status_code == 200
        data = response.json()
        # Should return cached count of 99
        assert data["overview"]["primary"]["count"] == 99

    def test_dashboard_caches_response_on_miss(self, client, db_session):
        """Dashboard caches response when cache is empty."""
        from unittest.mock import MagicMock, patch

        mock_redis = MagicMock()
        mock_redis.get.return_value = None  # Cache miss

        with patch("app.services.dashboard_stats.get_redis", return_value=mock_redis):
            response = client.get("/api/v1/stats/dashboard")

        assert response.status_code == 200
        # Verify cache was set
        mock_redis.setex.assert_called_once()

    def test_dashboard_works_without_redis(self, client, db_session):
        """Dashboard works normally when Redis is unavailable."""
        from unittest.mock import patch

        with patch("app.services.dashboard_stats.get_redis", return_value=None):
            response = client.get("/api/v1/stats/dashboard")

        assert response.status_code == 200
        data = response.json()
        assert "overview" in data
        assert "bindings" in data
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/perf-1002-dashboard-caching/backend && poetry run pytest tests/test_stats.py::TestDashboardCaching -v`

Expected: Tests fail (caching not integrated yet)

**Step 3: Commit failing tests**

```bash
git add backend/tests/test_stats.py
git commit -m "test: Add dashboard caching integration tests (TDD - failing)"
```

---

## Task 6: Integrate Caching into Dashboard Service

**Files:**
- Modify: `backend/app/services/dashboard_stats.py`

**Step 1: Add caching to get_dashboard_optimized**

Replace the `get_dashboard_optimized` function in `backend/app/services/dashboard_stats.py`:

```python
def get_dashboard_optimized(db: Session, reference_date: str = None, days: int = 30) -> dict:
    """Get all dashboard stats with optimized queries and caching.

    Caches the complete dashboard response for 5 minutes.
    Falls back to direct queries when Redis is unavailable.

    Args:
        db: Database session
        reference_date: Reference date for acquisitions (YYYY-MM-DD)
        days: Number of days for acquisition history

    Returns:
        dict matching DashboardResponse schema
    """
    import json
    import logging

    from app.cache import get_redis

    logger = logging.getLogger(__name__)

    # Build cache key based on parameters
    cache_key = f"dashboard:stats:{reference_date or 'default'}:{days}"

    # Try cache first
    client = get_redis()
    if client:
        try:
            cached_value = client.get(cache_key)
            if cached_value:
                logger.debug(f"Dashboard cache HIT: {cache_key}")
                return json.loads(cached_value)
        except Exception as e:
            logger.warning(f"Dashboard cache GET failed: {e}")

    logger.debug(f"Dashboard cache MISS: {cache_key}")

    # Cache miss - execute queries
    from app.api.v1.stats import (
        get_acquisitions_daily,
        get_bindings,
        get_by_author,
        get_by_publisher,
    )

    # Consolidated queries (2 queries instead of ~9)
    overview = get_overview_stats(db)
    dimensions = get_dimension_stats(db)

    # Individual queries that remain (complex logic)
    bindings = get_bindings(db)
    by_publisher = get_by_publisher(db)
    by_author = get_by_author(db)
    acquisitions_daily = get_acquisitions_daily(db, reference_date, days)

    result = {
        "overview": overview,
        "bindings": bindings,
        "by_era": dimensions["by_era"],
        "by_publisher": by_publisher,
        "by_author": by_author,
        "acquisitions_daily": acquisitions_daily,
        "by_condition": dimensions["by_condition"],
        "by_category": dimensions["by_category"],
    }

    # Store in cache
    if client:
        try:
            serialized = json.dumps(result, default=str)
            client.setex(cache_key, 300, serialized)  # 5 minute TTL
            logger.debug(f"Dashboard cached: {cache_key}")
        except Exception as e:
            logger.warning(f"Dashboard cache SET failed: {e}")

    return result
```

**Step 2: Run tests to verify they pass**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/perf-1002-dashboard-caching/backend && poetry run pytest tests/test_stats.py -v`

Expected: PASS (all tests including caching tests)

**Step 3: Commit integration**

```bash
git add backend/app/services/dashboard_stats.py
git commit -m "feat: Add Redis caching to dashboard endpoint"
```

---

## Task 7: Run Full Test Suite

**Files:** None (validation only)

**Step 1: Run all backend tests**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/perf-1002-dashboard-caching/backend && poetry run pytest -v`

Expected: All tests pass

**Step 2: Run linting**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/perf-1002-dashboard-caching/backend && poetry run ruff check .`

Expected: No errors

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/perf-1002-dashboard-caching/backend && poetry run ruff format --check .`

Expected: No formatting issues

**Step 3: Fix any issues found and commit**

If issues found, fix and commit:
```bash
git add -A
git commit -m "fix: Address linting/test issues"
```

---

## Task 8: Create ElastiCache Terraform Module

**Files:**
- Create: `infra/terraform/modules/elasticache/main.tf`
- Create: `infra/terraform/modules/elasticache/variables.tf`
- Create: `infra/terraform/modules/elasticache/outputs.tf`
- Create: `infra/terraform/modules/elasticache/versions.tf`

**Step 1: Create versions.tf**

Create `infra/terraform/modules/elasticache/versions.tf`:

```hcl
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}
```

**Step 2: Create variables.tf**

Create `infra/terraform/modules/elasticache/variables.tf`:

```hcl
variable "environment" {
  type        = string
  description = "Environment name (staging, prod)"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID for ElastiCache"
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnet IDs for ElastiCache (private subnets)"
}

variable "lambda_security_group_id" {
  type        = string
  description = "Lambda security group ID (for ingress rules)"
}

variable "tags" {
  type        = map(string)
  description = "Resource tags"
  default     = {}
}
```

**Step 3: Create main.tf**

Create `infra/terraform/modules/elasticache/main.tf`:

```hcl
# Security group for ElastiCache
resource "aws_security_group" "redis" {
  name_prefix = "bmx-${var.environment}-redis-"
  vpc_id      = var.vpc_id
  description = "Security group for ElastiCache Redis"

  ingress {
    description     = "Redis from Lambda"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [var.lambda_security_group_id]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "bmx-${var.environment}-redis-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# ElastiCache Serverless (Redis)
resource "aws_elasticache_serverless_cache" "this" {
  engine = "redis"
  name   = "bmx-${var.environment}-cache"

  cache_usage_limits {
    data_storage {
      maximum = 1
      unit    = "GB"
    }
    ecpu_per_second {
      maximum = 1000
    }
  }

  daily_snapshot_time      = "05:00"
  description              = "Dashboard stats cache for ${var.environment}"
  major_engine_version     = "7"
  snapshot_retention_limit = 1
  subnet_ids               = var.subnet_ids
  security_group_ids       = [aws_security_group.redis.id]

  tags = merge(var.tags, {
    Name = "bmx-${var.environment}-cache"
  })
}
```

**Step 4: Create outputs.tf**

Create `infra/terraform/modules/elasticache/outputs.tf`:

```hcl
output "redis_endpoint" {
  description = "Redis endpoint URL"
  value       = "rediss://${aws_elasticache_serverless_cache.this.endpoint[0].address}:${aws_elasticache_serverless_cache.this.endpoint[0].port}"
}

output "security_group_id" {
  description = "ElastiCache security group ID"
  value       = aws_security_group.redis.id
}

output "cache_name" {
  description = "ElastiCache serverless cache name"
  value       = aws_elasticache_serverless_cache.this.name
}
```

**Step 5: Commit module**

```bash
git add infra/terraform/modules/elasticache/
git commit -m "feat: Add ElastiCache Terraform module"
```

---

## Task 9: Integrate ElastiCache into Staging

**Files:**
- Modify: `infra/terraform/main.tf`
- Modify: `infra/terraform/envs/staging.tfvars`

**Step 1: Add elasticache module to main.tf**

Add to `infra/terraform/main.tf` (after existing modules):

```hcl
# ElastiCache for dashboard caching (staging only initially)
module "elasticache" {
  count  = var.enable_elasticache ? 1 : 0
  source = "./modules/elasticache"

  environment              = var.environment
  vpc_id                   = module.vpc.vpc_id
  subnet_ids               = module.vpc.private_subnet_ids
  lambda_security_group_id = module.api_lambda.security_group_id

  tags = local.common_tags
}
```

**Step 2: Add variable to variables.tf**

Add to `infra/terraform/variables.tf`:

```hcl
variable "enable_elasticache" {
  type        = bool
  description = "Enable ElastiCache for dashboard caching"
  default     = false
}
```

**Step 3: Add output to outputs.tf**

Add to `infra/terraform/outputs.tf`:

```hcl
output "redis_url" {
  description = "Redis URL for Lambda environment variable"
  value       = var.enable_elasticache ? module.elasticache[0].redis_endpoint : ""
  sensitive   = true
}
```

**Step 4: Update Lambda environment variables**

In `infra/terraform/main.tf`, update the `api_lambda` module's environment_variables:

Add `BMX_REDIS_URL = var.enable_elasticache ? module.elasticache[0].redis_endpoint : ""`

**Step 5: Enable in staging.tfvars**

Add to `infra/terraform/envs/staging.tfvars`:

```hcl
enable_elasticache = true
```

**Step 6: Validate Terraform**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/perf-1002-dashboard-caching/infra/terraform && terraform fmt -recursive`

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/perf-1002-dashboard-caching/infra/terraform && terraform validate`

Expected: Success

**Step 7: Commit integration**

```bash
git add infra/terraform/
git commit -m "feat: Integrate ElastiCache into staging infrastructure"
```

---

## Task 10: Final Validation and PR Creation

**Files:** None

**Step 1: Run all tests one final time**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/perf-1002-dashboard-caching/backend && poetry run pytest -v`

Expected: All tests pass

**Step 2: Run linting**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/perf-1002-dashboard-caching/backend && poetry run ruff check .`

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/perf-1002-dashboard-caching/backend && poetry run ruff format --check .`

Expected: No issues

**Step 3: Push branch**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/perf-1002-dashboard-caching && git push -u origin perf/1002-dashboard-caching`

**Step 4: Create PR to staging**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/perf-1002-dashboard-caching
gh pr create --base staging --title "perf: Add Redis caching for dashboard stats (#1002)" --body "## Summary
- Add ElastiCache Serverless (Redis) infrastructure for staging
- Implement cache module with 5-minute TTL
- Integrate caching into /stats/dashboard endpoint
- Graceful degradation when Redis unavailable

## Architecture
- Single cache key per parameter set: \`dashboard:stats:{date}:{days}\`
- TTL-only invalidation (5 minutes)
- VPC-attached Lambda connects to ElastiCache

## Test Plan
- [ ] CI passes
- [ ] Terraform plan shows expected ElastiCache resources
- [ ] Manual staging validation after merge

Closes #1002 (Phase 1 - Staging)

## Related
- Design doc: docs/plans/2026-01-10-dashboard-caching-design.md"
```

**Step 5: Request user review**

STOP - Wait for user to review PR before merging to staging.

---

## Post-Staging Tasks (After User Review)

### Task 11: Apply Terraform to Staging

After PR is merged to staging:

```bash
cd /Users/mark/projects/bluemoxon/infra/terraform
AWS_PROFILE=bmx-staging terraform plan -var-file=envs/staging.tfvars
AWS_PROFILE=bmx-staging terraform apply -var-file=envs/staging.tfvars
```

### Task 12: Validate in Staging

```bash
# Check health
curl -s https://staging.api.bluemoxon.com/api/v1/health/deep | jq

# Call dashboard twice, compare timing
time curl -s https://staging.api.bluemoxon.com/api/v1/stats/dashboard > /dev/null
time curl -s https://staging.api.bluemoxon.com/api/v1/stats/dashboard > /dev/null
```

Second call should be faster (cached).

### Task 13: Promote to Production

After staging validation:

1. Add `enable_elasticache = true` to `envs/prod.tfvars`
2. Create PR from `staging` to `main`
3. Wait for user review
4. Merge and apply Terraform to production
