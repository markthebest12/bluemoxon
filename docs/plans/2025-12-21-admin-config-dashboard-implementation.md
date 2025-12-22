# Admin Config Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expand `/admin/config` from currency rates editor to comprehensive tabbed dashboard with system status, scoring config, and entity tiers.

**Architecture:** Single new backend endpoint (`GET /admin/system-info`) aggregates health checks, versions, scoring constants, and tiered entities. Frontend transforms from single-purpose form to tabbed interface with 4 tabs. Navigation updated to allow editor role access.

**Tech Stack:** FastAPI (backend), Vue 3 + TypeScript (frontend), Tailwind CSS (styling)

**Related Work:** Author tier scoring (#528) runs in parallel - Entity Tiers tab will display whatever tiers exist in database.

---

## Task 1: Backend - Add Cold Start Detection

**Files:**
- Modify: `backend/app/main.py`

**Step 1: Add cold start flag**

Add at module level (after imports, before app creation):

```python
# Cold start detection - set True on module load, cleared after first request
_is_cold_start = True
```

**Step 2: Add middleware to track cold start**

Add after CORS middleware setup:

```python
@app.middleware("http")
async def cold_start_middleware(request: Request, call_next):
    global _is_cold_start
    response = await call_next(request)
    # Add cold start header for debugging
    response.headers["X-Cold-Start"] = str(_is_cold_start)
    _is_cold_start = False
    return response
```

**Step 3: Export cold start getter**

Add function:

```python
def get_cold_start_status() -> bool:
    """Return True if this is the first request since Lambda cold start."""
    return _is_cold_start
```

**Step 4: Run tests to verify no breakage**

Run: `poetry run pytest tests/ -q --tb=short`
Expected: All tests pass

**Step 5: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: add cold start detection for admin dashboard"
```

---

## Task 2: Backend - Add System Info Endpoint

**Files:**
- Modify: `backend/app/api/v1/admin.py`
- Reference: `backend/app/api/v1/health.py` (reuse check functions)
- Reference: `backend/app/services/tiered_scoring.py` (import constants)
- Reference: `backend/app/services/bedrock.py` (import MODEL_IDS)

**Step 1: Add imports to admin.py**

Add to existing imports:

```python
from datetime import UTC, datetime

from app.api.v1.health import check_cognito, check_database, check_s3
from app.main import get_cold_start_status
from app.models.author import Author
from app.models.binder import Binder
from app.models.publisher import Publisher
from app.services import tiered_scoring
from app.services.bedrock import MODEL_IDS
from app.version import get_version_info
```

**Step 2: Add response schema**

Add after existing schemas:

```python
class HealthCheck(BaseModel):
    """Individual health check result."""
    status: str
    latency_ms: float | None = None
    error: str | None = None
    book_count: int | None = None
    bucket: str | None = None
    user_pool: str | None = None
    reason: str | None = None


class HealthChecks(BaseModel):
    """All health check results."""
    database: HealthCheck
    s3: HealthCheck
    cognito: HealthCheck


class HealthInfo(BaseModel):
    """Health summary."""
    overall: str
    total_latency_ms: float
    checks: HealthChecks


class SystemInfo(BaseModel):
    """System version and deployment info."""
    version: str
    git_sha: str | None = None
    deploy_time: str | None = None
    environment: str


class EntityTier(BaseModel):
    """Entity with tier information."""
    name: str
    tier: str


class EntityTiers(BaseModel):
    """All tiered entities."""
    authors: list[EntityTier]
    publishers: list[EntityTier]
    binders: list[EntityTier]


class SystemInfoResponse(BaseModel):
    """Complete system info response."""
    is_cold_start: bool
    timestamp: str
    system: SystemInfo
    health: HealthInfo
    models: dict[str, str]
    scoring_config: dict
    entity_tiers: EntityTiers
```

**Step 3: Add helper to collect scoring config**

Add after schemas:

```python
def get_scoring_config() -> dict:
    """Collect all scoring constants from tiered_scoring module."""
    return {
        "quality_points": {
            "publisher_tier_1": tiered_scoring.QUALITY_TIER_1_PUBLISHER,
            "publisher_tier_2": tiered_scoring.QUALITY_TIER_2_PUBLISHER,
            "binder_tier_1": tiered_scoring.QUALITY_TIER_1_BINDER,
            "binder_tier_2": tiered_scoring.QUALITY_TIER_2_BINDER,
            "double_tier_1_bonus": tiered_scoring.QUALITY_DOUBLE_TIER_1_BONUS,
            "era_bonus": tiered_scoring.QUALITY_ERA_BONUS,
            "condition_fine": tiered_scoring.QUALITY_CONDITION_FINE,
            "condition_good": tiered_scoring.QUALITY_CONDITION_GOOD,
            "complete_set": tiered_scoring.QUALITY_COMPLETE_SET,
            "author_priority_cap": tiered_scoring.QUALITY_AUTHOR_PRIORITY_CAP,
            "duplicate_penalty": tiered_scoring.QUALITY_DUPLICATE_PENALTY,
            "large_volume_penalty": tiered_scoring.QUALITY_LARGE_VOLUME_PENALTY,
        },
        "strategic_points": {
            "publisher_match": tiered_scoring.STRATEGIC_PUBLISHER_MATCH,
            "new_author": tiered_scoring.STRATEGIC_NEW_AUTHOR,
            "second_work": tiered_scoring.STRATEGIC_SECOND_WORK,
            "completes_set": tiered_scoring.STRATEGIC_COMPLETES_SET,
        },
        "thresholds": {
            "price_excellent": float(tiered_scoring.PRICE_EXCELLENT_THRESHOLD),
            "price_good": float(tiered_scoring.PRICE_GOOD_THRESHOLD),
            "price_fair": float(tiered_scoring.PRICE_FAIR_THRESHOLD),
            "strategic_floor": tiered_scoring.STRATEGIC_FIT_FLOOR,
            "quality_floor": tiered_scoring.QUALITY_FLOOR,
        },
        "weights": {
            "quality": tiered_scoring.QUALITY_WEIGHT,
            "strategic_fit": tiered_scoring.STRATEGIC_FIT_WEIGHT,
        },
        "offer_discounts": {
            "70-79": float(tiered_scoring.OFFER_DISCOUNTS[(70, 79)]),
            "60-69": float(tiered_scoring.OFFER_DISCOUNTS[(60, 69)]),
            "50-59": float(tiered_scoring.OFFER_DISCOUNTS[(50, 59)]),
            "40-49": float(tiered_scoring.OFFER_DISCOUNTS[(40, 49)]),
            "0-39": float(tiered_scoring.OFFER_DISCOUNTS[(0, 39)]),
            "strategic_floor": float(tiered_scoring.STRATEGIC_FLOOR_DISCOUNT),
            "quality_floor": float(tiered_scoring.QUALITY_FLOOR_DISCOUNT),
        },
        "era_boundaries": {
            "romantic_start": tiered_scoring.ROMANTIC_START,
            "romantic_end": tiered_scoring.ROMANTIC_END,
            "victorian_start": tiered_scoring.VICTORIAN_START,
            "victorian_end": tiered_scoring.VICTORIAN_END,
        },
    }
```

**Step 4: Add system-info endpoint**

Add after existing endpoints:

```python
@router.get("/system-info", response_model=SystemInfoResponse)
def get_system_info(db: Session = Depends(get_db)):
    """Get comprehensive system information for admin dashboard.

    Returns version info, health checks, scoring configuration,
    and tiered entities (authors, publishers, binders).
    """
    import time
    start = time.time()

    # Get cold start status
    is_cold_start = get_cold_start_status()

    # Get version info
    version_info = get_version_info()

    # Run health checks
    db_health = check_database(db)
    s3_health = check_s3()
    cognito_health = check_cognito()

    # Determine overall health
    statuses = [db_health["status"], s3_health["status"], cognito_health["status"]]
    if all(s in ("healthy", "skipped") for s in statuses):
        overall = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall = "unhealthy"
    else:
        overall = "degraded"

    total_latency = round((time.time() - start) * 1000, 2)

    # Get tiered entities
    authors = db.query(Author).filter(
        Author.tier.in_(["TIER_1", "TIER_2", "TIER_3"])
    ).order_by(Author.tier, Author.name).all()

    publishers = db.query(Publisher).filter(
        Publisher.tier.in_(["TIER_1", "TIER_2", "TIER_3"])
    ).order_by(Publisher.tier, Publisher.name).all()

    binders = db.query(Binder).filter(
        Binder.tier.in_(["TIER_1", "TIER_2", "TIER_3"])
    ).order_by(Binder.tier, Binder.name).all()

    return SystemInfoResponse(
        is_cold_start=is_cold_start,
        timestamp=datetime.now(UTC).isoformat(),
        system=SystemInfo(
            version=version_info.get("version", "unknown"),
            git_sha=version_info.get("git_sha"),
            deploy_time=version_info.get("deploy_time"),
            environment=version_info.get("environment", "unknown"),
        ),
        health=HealthInfo(
            overall=overall,
            total_latency_ms=total_latency,
            checks=HealthChecks(
                database=HealthCheck(**db_health),
                s3=HealthCheck(**s3_health),
                cognito=HealthCheck(**cognito_health),
            ),
        ),
        models=MODEL_IDS,
        scoring_config=get_scoring_config(),
        entity_tiers=EntityTiers(
            authors=[EntityTier(name=a.name, tier=a.tier) for a in authors],
            publishers=[EntityTier(name=p.name, tier=p.tier) for p in publishers],
            binders=[EntityTier(name=b.name, tier=b.tier) for b in binders],
        ),
    )
```

**Step 5: Run linter**

Run: `poetry run ruff check backend/app/api/v1/admin.py --fix`
Expected: No errors or auto-fixed

**Step 6: Run tests**

Run: `poetry run pytest tests/ -q --tb=short`
Expected: All tests pass

**Step 7: Commit**

```bash
git add backend/app/api/v1/admin.py
git commit -m "feat: add /admin/system-info endpoint for dashboard"
```

---

## Task 3: Backend - Add Test for System Info Endpoint

**Files:**
- Create: `backend/tests/api/v1/test_admin_system_info.py`

**Step 1: Write the test file**

```python
"""Tests for admin system-info endpoint."""

import pytest
from fastapi.testclient import TestClient


def test_get_system_info_returns_expected_structure(client: TestClient, mock_editor_auth):
    """Test that system-info returns all expected sections."""
    response = client.get("/api/v1/admin/system-info")
    assert response.status_code == 200

    data = response.json()

    # Check top-level keys
    assert "is_cold_start" in data
    assert "timestamp" in data
    assert "system" in data
    assert "health" in data
    assert "models" in data
    assert "scoring_config" in data
    assert "entity_tiers" in data


def test_get_system_info_system_section(client: TestClient, mock_editor_auth):
    """Test system section has version info."""
    response = client.get("/api/v1/admin/system-info")
    data = response.json()

    system = data["system"]
    assert "version" in system
    assert "environment" in system


def test_get_system_info_health_section(client: TestClient, mock_editor_auth):
    """Test health section has expected checks."""
    response = client.get("/api/v1/admin/system-info")
    data = response.json()

    health = data["health"]
    assert "overall" in health
    assert "total_latency_ms" in health
    assert "checks" in health

    checks = health["checks"]
    assert "database" in checks
    assert "s3" in checks
    assert "cognito" in checks


def test_get_system_info_scoring_config(client: TestClient, mock_editor_auth):
    """Test scoring config has all expected sections."""
    response = client.get("/api/v1/admin/system-info")
    data = response.json()

    config = data["scoring_config"]
    assert "quality_points" in config
    assert "strategic_points" in config
    assert "thresholds" in config
    assert "weights" in config
    assert "offer_discounts" in config

    # Verify specific values match constants
    assert config["quality_points"]["publisher_tier_1"] == 25
    assert config["weights"]["quality"] == 0.6


def test_get_system_info_entity_tiers(client: TestClient, mock_editor_auth):
    """Test entity tiers section structure."""
    response = client.get("/api/v1/admin/system-info")
    data = response.json()

    tiers = data["entity_tiers"]
    assert "authors" in tiers
    assert "publishers" in tiers
    assert "binders" in tiers

    # All should be lists (may be empty if no tiered entities)
    assert isinstance(tiers["authors"], list)
    assert isinstance(tiers["publishers"], list)
    assert isinstance(tiers["binders"], list)


def test_get_system_info_models(client: TestClient, mock_editor_auth):
    """Test models section has bedrock model IDs."""
    response = client.get("/api/v1/admin/system-info")
    data = response.json()

    models = data["models"]
    assert "sonnet" in models
    assert "opus" in models
    assert "claude" in models["sonnet"].lower()
```

**Step 2: Run the tests**

Run: `poetry run pytest tests/api/v1/test_admin_system_info.py -v`
Expected: All tests pass

**Step 3: Commit**

```bash
git add backend/tests/api/v1/test_admin_system_info.py
git commit -m "test: add tests for /admin/system-info endpoint"
```

---

## Task 4: Frontend - Add requiresEditor Router Guard

**Files:**
- Modify: `frontend/src/router/index.ts`

**Step 1: Add requiresEditor guard logic**

Find the `router.beforeEach` section and update the guard logic. After the `requiresAdmin` check, add editor check:

Change this block:
```typescript
  } else if (to.meta.requiresAdmin && !authStore.isAdmin) {
    // Admin-only routes redirect to home if not admin
    next({ name: "home" });
  } else if (to.name === "login" && authStore.isAuthenticated && !authStore.needsMfa) {
```

To:
```typescript
  } else if (to.meta.requiresAdmin && !authStore.isAdmin) {
    // Admin-only routes redirect to home if not admin
    next({ name: "home" });
  } else if (to.meta.requiresEditor && !authStore.isEditor) {
    // Editor-only routes redirect to home if not editor
    next({ name: "home" });
  } else if (to.name === "login" && authStore.isAuthenticated && !authStore.needsMfa) {
```

**Step 2: Update admin-config route meta**

Find the `/admin/config` route and change `requiresAdmin: true` to `requiresEditor: true`:

```typescript
    {
      path: "/admin/config",
      name: "admin-config",
      component: () => import("@/views/AdminConfigView.vue"),
      meta: { requiresAuth: true, requiresEditor: true },
    },
```

**Step 3: Run type check**

Run: `cd ../frontend && npm run type-check`
Expected: No errors

**Step 4: Commit**

```bash
git add frontend/src/router/index.ts
git commit -m "feat: add requiresEditor guard, allow editors to access /admin/config"
```

---

## Task 5: Frontend - Add Config Menu Item to NavBar

**Files:**
- Modify: `frontend/src/components/layout/NavBar.vue`

**Step 1: Add Config link to desktop dropdown**

Find the dropdown menu section (after Profile link, before Admin Settings). Add:

```vue
                  <RouterLink
                    v-if="authStore.isEditor"
                    to="/admin/config"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  >
                    Config
                  </RouterLink>
```

Insert between:
```vue
                  <RouterLink
                    to="/profile"
                    ...
                  >
                    Profile
                  </RouterLink>
                  <!-- INSERT HERE -->
                  <RouterLink
                    v-if="authStore.isAdmin"
                    to="/admin"
                    ...
                  >
                    Admin Settings
                  </RouterLink>
```

**Step 2: Add Config link to mobile menu**

Find the mobile menu section (after Profile link, before Admin Settings). Add:

```vue
          <RouterLink
            v-if="authStore.isEditor"
            to="/admin/config"
            class="block py-3 text-victorian-paper-cream/80 hover:text-victorian-gold-light border-b border-victorian-hunter-700"
            @click="closeMobileMenu"
          >
            Config
          </RouterLink>
```

**Step 3: Run type check**

Run: `npm run type-check`
Expected: No errors

**Step 4: Commit**

```bash
git add frontend/src/components/layout/NavBar.vue
git commit -m "feat: add Config menu item for editors and admins"
```

---

## Task 6: Frontend - Add API Service Method

**Files:**
- Modify: `frontend/src/services/api.ts` (or create type if needed)

**Step 1: Check existing api service structure**

Read `frontend/src/services/api.ts` to understand the pattern.

**Step 2: Add type definitions**

Create `frontend/src/types/admin.ts`:

```typescript
export interface HealthCheck {
  status: string;
  latency_ms?: number;
  error?: string;
  book_count?: number;
  bucket?: string;
  user_pool?: string;
  reason?: string;
}

export interface HealthInfo {
  overall: string;
  total_latency_ms: number;
  checks: {
    database: HealthCheck;
    s3: HealthCheck;
    cognito: HealthCheck;
  };
}

export interface SystemInfo {
  version: string;
  git_sha?: string;
  deploy_time?: string;
  environment: string;
}

export interface EntityTier {
  name: string;
  tier: string;
}

export interface EntityTiers {
  authors: EntityTier[];
  publishers: EntityTier[];
  binders: EntityTier[];
}

export interface ScoringConfig {
  quality_points: Record<string, number>;
  strategic_points: Record<string, number>;
  thresholds: Record<string, number>;
  weights: Record<string, number>;
  offer_discounts: Record<string, number>;
  era_boundaries: Record<string, number>;
}

export interface SystemInfoResponse {
  is_cold_start: boolean;
  timestamp: string;
  system: SystemInfo;
  health: HealthInfo;
  models: Record<string, string>;
  scoring_config: ScoringConfig;
  entity_tiers: EntityTiers;
}
```

**Step 3: Commit**

```bash
git add frontend/src/types/admin.ts
git commit -m "feat: add TypeScript types for admin system-info API"
```

---

## Task 7: Frontend - Refactor AdminConfigView to Tabbed Interface

**Files:**
- Modify: `frontend/src/views/AdminConfigView.vue`

**Step 1: Rewrite the entire component**

Replace contents with:

```vue
<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { api } from "@/services/api";
import type { SystemInfoResponse } from "@/types/admin";

// Tab state
const activeTab = ref<"settings" | "status" | "scoring" | "tiers">("settings");

// Settings tab (existing functionality)
const config = ref({ gbp_to_usd_rate: 1.28, eur_to_usd_rate: 1.1 });
const saving = ref(false);
const settingsMessage = ref("");

// System info (for other tabs)
const systemInfo = ref<SystemInfoResponse | null>(null);
const loadingInfo = ref(false);
const infoError = ref("");

// Key tunables to highlight in scoring config
const keyTunables = new Set([
  "publisher_tier_1",
  "publisher_tier_2",
  "binder_tier_1",
  "binder_tier_2",
  "author_priority_cap",
  "publisher_match",
  "new_author",
  "quality",
  "strategic_fit",
  "strategic_floor",
  "quality_floor",
  "strategic_floor",
  "quality_floor",
]);

const isKeyTunable = (key: string) => keyTunables.has(key);

onMounted(async () => {
  await loadConfig();
  await loadSystemInfo();
});

async function loadConfig() {
  try {
    const res = await api.get("/admin/config");
    config.value = res.data;
  } catch (e) {
    console.error("Failed to load config:", e);
  }
}

async function saveConfig() {
  saving.value = true;
  settingsMessage.value = "";
  try {
    await api.put("/admin/config", config.value);
    settingsMessage.value = "Saved successfully";
    setTimeout(() => {
      settingsMessage.value = "";
    }, 3000);
  } catch (e) {
    settingsMessage.value = "Failed to save";
    console.error("Failed to save config:", e);
  } finally {
    saving.value = false;
  }
}

async function loadSystemInfo() {
  loadingInfo.value = true;
  infoError.value = "";
  try {
    const res = await api.get("/admin/system-info");
    systemInfo.value = res.data;
  } catch (e) {
    infoError.value = "Failed to load system info";
    console.error("Failed to load system info:", e);
  } finally {
    loadingInfo.value = false;
  }
}

async function refreshSystemInfo() {
  await loadSystemInfo();
}

// Computed helpers
const hasHealthIssues = computed(() => {
  if (!systemInfo.value) return false;
  return systemInfo.value.health.overall !== "healthy";
});

const healthStatusClass = (status: string) => {
  switch (status) {
    case "healthy":
      return "text-green-600";
    case "unhealthy":
      return "text-red-600";
    case "skipped":
      return "text-gray-400";
    default:
      return "text-yellow-600";
  }
};

const healthIcon = (status: string) => {
  switch (status) {
    case "healthy":
      return "✓";
    case "unhealthy":
      return "✗";
    case "skipped":
      return "○";
    default:
      return "!";
  }
};

// Group entities by tier
const groupedAuthors = computed(() => groupByTier(systemInfo.value?.entity_tiers.authors || []));
const groupedPublishers = computed(() => groupByTier(systemInfo.value?.entity_tiers.publishers || []));
const groupedBinders = computed(() => groupByTier(systemInfo.value?.entity_tiers.binders || []));

function groupByTier(entities: { name: string; tier: string }[]) {
  const groups: Record<string, string[]> = { TIER_1: [], TIER_2: [], TIER_3: [] };
  for (const e of entities) {
    if (groups[e.tier]) {
      groups[e.tier].push(e.name);
    }
  }
  return groups;
}

function formatTierLabel(tier: string) {
  return tier.replace("TIER_", "Tier ");
}
</script>

<template>
  <div class="max-w-6xl mx-auto p-6">
    <h1 class="text-2xl font-bold mb-6">Admin Configuration</h1>

    <!-- Health Alert Banner -->
    <div
      v-if="hasHealthIssues && systemInfo"
      class="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg"
    >
      <div class="flex items-center gap-2 text-red-700">
        <span class="text-xl">⚠️</span>
        <span class="font-medium">System health issues detected</span>
        <span class="text-sm text-red-600">
          ({{ systemInfo.health.overall }})
        </span>
      </div>
    </div>

    <!-- Tab Navigation -->
    <div class="border-b border-gray-200 mb-6">
      <nav class="-mb-px flex space-x-8">
        <button
          @click="activeTab = 'settings'"
          :class="[
            'py-4 px-1 border-b-2 font-medium text-sm',
            activeTab === 'settings'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
          ]"
        >
          Settings
        </button>
        <button
          @click="activeTab = 'status'"
          :class="[
            'py-4 px-1 border-b-2 font-medium text-sm',
            activeTab === 'status'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
          ]"
        >
          System Status
        </button>
        <button
          @click="activeTab = 'scoring'"
          :class="[
            'py-4 px-1 border-b-2 font-medium text-sm',
            activeTab === 'scoring'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
          ]"
        >
          Scoring Config
        </button>
        <button
          @click="activeTab = 'tiers'"
          :class="[
            'py-4 px-1 border-b-2 font-medium text-sm',
            activeTab === 'tiers'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
          ]"
        >
          Entity Tiers
        </button>
      </nav>
    </div>

    <!-- Settings Tab -->
    <div v-if="activeTab === 'settings'" class="bg-white rounded-lg shadow p-6 space-y-4">
      <h2 class="text-lg font-semibold">Currency Conversion Rates</h2>
      <div class="grid grid-cols-2 gap-4">
        <label class="block">
          <span class="text-sm text-gray-700">GBP to USD</span>
          <input
            v-model.number="config.gbp_to_usd_rate"
            type="number"
            step="0.01"
            class="mt-1 block w-full rounded border-gray-300 shadow-sm"
          />
        </label>
        <label class="block">
          <span class="text-sm text-gray-700">EUR to USD</span>
          <input
            v-model.number="config.eur_to_usd_rate"
            type="number"
            step="0.01"
            class="mt-1 block w-full rounded border-gray-300 shadow-sm"
          />
        </label>
      </div>
      <div class="flex items-center gap-4">
        <button
          @click="saveConfig"
          :disabled="saving"
          class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {{ saving ? "Saving..." : "Save" }}
        </button>
        <span v-if="settingsMessage" class="text-sm text-green-600">{{ settingsMessage }}</span>
      </div>
    </div>

    <!-- System Status Tab -->
    <div v-else-if="activeTab === 'status'" class="space-y-6">
      <div class="flex justify-end">
        <button
          @click="refreshSystemInfo"
          :disabled="loadingInfo"
          class="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
        >
          {{ loadingInfo ? "Loading..." : "Refresh" }}
        </button>
      </div>

      <div v-if="infoError" class="p-4 bg-red-50 text-red-700 rounded">{{ infoError }}</div>

      <div v-else-if="systemInfo" class="space-y-6">
        <!-- Version & Deployment -->
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-4">Version & Deployment</h3>
          <dl class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt class="text-gray-500">App Version</dt>
              <dd class="font-mono">{{ systemInfo.system.version }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Git SHA</dt>
              <dd class="font-mono">{{ systemInfo.system.git_sha || "N/A" }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Deploy Time</dt>
              <dd class="font-mono">{{ systemInfo.system.deploy_time || "N/A" }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Environment</dt>
              <dd class="font-mono">{{ systemInfo.system.environment }}</dd>
            </div>
          </dl>
          <div v-if="systemInfo.is_cold_start" class="mt-4 text-sm text-amber-600">
            ⚡ Cold Start - latencies may be elevated
          </div>
        </div>

        <!-- Health Checks -->
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-4">Health Checks</h3>
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span :class="healthStatusClass(systemInfo.health.checks.database.status)">
                  {{ healthIcon(systemInfo.health.checks.database.status) }}
                </span>
                <span>Database</span>
                <span class="text-xs text-gray-400">
                  ({{ systemInfo.health.checks.database.book_count }} books)
                </span>
              </div>
              <span class="text-sm text-gray-500">
                {{ systemInfo.health.checks.database.latency_ms }}ms
              </span>
            </div>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span :class="healthStatusClass(systemInfo.health.checks.s3.status)">
                  {{ healthIcon(systemInfo.health.checks.s3.status) }}
                </span>
                <span>S3 Images</span>
                <span class="text-xs text-gray-400">
                  ({{ systemInfo.health.checks.s3.bucket }})
                </span>
              </div>
              <span class="text-sm text-gray-500">
                {{ systemInfo.health.checks.s3.latency_ms }}ms
              </span>
            </div>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span :class="healthStatusClass(systemInfo.health.checks.cognito.status)">
                  {{ healthIcon(systemInfo.health.checks.cognito.status) }}
                </span>
                <span>Cognito</span>
                <span v-if="systemInfo.health.checks.cognito.reason" class="text-xs text-gray-400">
                  ({{ systemInfo.health.checks.cognito.reason }})
                </span>
              </div>
              <span class="text-sm text-gray-500">
                {{ systemInfo.health.checks.cognito.latency_ms || "-" }}ms
              </span>
            </div>
          </div>
          <div class="mt-4 pt-4 border-t text-sm text-gray-500">
            Total latency: {{ systemInfo.health.total_latency_ms }}ms
          </div>
        </div>

        <!-- Bedrock Models -->
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-4">Bedrock Models</h3>
          <dl class="space-y-2 text-sm">
            <div v-for="(model, key) in systemInfo.models" :key="key" class="flex gap-2">
              <dt class="text-gray-500 w-20">{{ key }}:</dt>
              <dd class="font-mono text-xs">{{ model }}</dd>
            </div>
          </dl>
        </div>
      </div>
    </div>

    <!-- Scoring Config Tab -->
    <div v-else-if="activeTab === 'scoring'" class="space-y-6">
      <div class="flex justify-between items-center">
        <p class="text-sm text-gray-500">★ = Key tunable</p>
        <button
          @click="refreshSystemInfo"
          :disabled="loadingInfo"
          class="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
        >
          {{ loadingInfo ? "Loading..." : "Refresh" }}
        </button>
      </div>

      <div v-if="systemInfo" class="grid md:grid-cols-2 gap-6">
        <!-- Quality Points -->
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-4">Quality Score Points</h3>
          <dl class="space-y-1 text-sm">
            <div
              v-for="(value, key) in systemInfo.scoring_config.quality_points"
              :key="key"
              class="flex justify-between"
              :class="{ 'bg-yellow-50 -mx-2 px-2 py-0.5 rounded': isKeyTunable(key) }"
            >
              <dt>
                <span v-if="isKeyTunable(key)" class="text-yellow-600">★ </span>
                {{ key.replace(/_/g, " ") }}
              </dt>
              <dd class="font-mono">{{ value }} pts</dd>
            </div>
          </dl>
        </div>

        <!-- Strategic Points -->
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-4">Strategic Fit Points</h3>
          <dl class="space-y-1 text-sm">
            <div
              v-for="(value, key) in systemInfo.scoring_config.strategic_points"
              :key="key"
              class="flex justify-between"
              :class="{ 'bg-yellow-50 -mx-2 px-2 py-0.5 rounded': isKeyTunable(key) }"
            >
              <dt>
                <span v-if="isKeyTunable(key)" class="text-yellow-600">★ </span>
                {{ key.replace(/_/g, " ") }}
              </dt>
              <dd class="font-mono">{{ value }} pts</dd>
            </div>
          </dl>
        </div>

        <!-- Thresholds -->
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-4">Thresholds</h3>
          <dl class="space-y-1 text-sm">
            <div
              v-for="(value, key) in systemInfo.scoring_config.thresholds"
              :key="key"
              class="flex justify-between"
              :class="{ 'bg-yellow-50 -mx-2 px-2 py-0.5 rounded': isKeyTunable(key) }"
            >
              <dt>
                <span v-if="isKeyTunable(key)" class="text-yellow-600">★ </span>
                {{ key.replace(/_/g, " ") }}
              </dt>
              <dd class="font-mono">
                {{ key.includes("price") ? `${(value * 100).toFixed(0)}%` : value }}
              </dd>
            </div>
          </dl>
        </div>

        <!-- Weights -->
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-4">Combined Score Weights</h3>
          <dl class="space-y-1 text-sm">
            <div
              v-for="(value, key) in systemInfo.scoring_config.weights"
              :key="key"
              class="flex justify-between"
              :class="{ 'bg-yellow-50 -mx-2 px-2 py-0.5 rounded': isKeyTunable(key) }"
            >
              <dt>
                <span v-if="isKeyTunable(key)" class="text-yellow-600">★ </span>
                {{ key.replace(/_/g, " ") }}
              </dt>
              <dd class="font-mono">{{ (value * 100).toFixed(0) }}%</dd>
            </div>
          </dl>
        </div>

        <!-- Offer Discounts -->
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-4">Offer Discounts</h3>
          <dl class="space-y-1 text-sm">
            <div
              v-for="(value, key) in systemInfo.scoring_config.offer_discounts"
              :key="key"
              class="flex justify-between"
              :class="{ 'bg-yellow-50 -mx-2 px-2 py-0.5 rounded': isKeyTunable(key) }"
            >
              <dt>
                <span v-if="isKeyTunable(key)" class="text-yellow-600">★ </span>
                {{ key.includes("-") ? `Score ${key}` : key.replace(/_/g, " ") }}
              </dt>
              <dd class="font-mono">{{ (value * 100).toFixed(0) }}% below FMV</dd>
            </div>
          </dl>
        </div>

        <!-- Era Boundaries -->
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-4">Era Boundaries</h3>
          <dl class="space-y-1 text-sm">
            <div
              v-for="(value, key) in systemInfo.scoring_config.era_boundaries"
              :key="key"
              class="flex justify-between"
            >
              <dt>{{ key.replace(/_/g, " ") }}</dt>
              <dd class="font-mono">{{ value }}</dd>
            </div>
          </dl>
        </div>
      </div>
    </div>

    <!-- Entity Tiers Tab -->
    <div v-else-if="activeTab === 'tiers'" class="space-y-6">
      <div class="flex justify-end">
        <button
          @click="refreshSystemInfo"
          :disabled="loadingInfo"
          class="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
        >
          {{ loadingInfo ? "Loading..." : "Refresh" }}
        </button>
      </div>

      <div v-if="systemInfo" class="grid md:grid-cols-3 gap-6">
        <!-- Authors -->
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-4">Authors</h3>
          <div class="space-y-4">
            <div v-for="tier in ['TIER_1', 'TIER_2', 'TIER_3']" :key="tier">
              <h4 class="text-sm font-medium text-gray-500 mb-2">{{ formatTierLabel(tier) }}</h4>
              <ul v-if="groupedAuthors[tier]?.length" class="space-y-1 text-sm">
                <li v-for="name in groupedAuthors[tier]" :key="name">• {{ name }}</li>
              </ul>
              <p v-else class="text-sm text-gray-400 italic">None</p>
            </div>
          </div>
          <p class="mt-4 text-xs text-gray-400">
            {{ systemInfo.entity_tiers.authors.length }} total
          </p>
        </div>

        <!-- Publishers -->
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-4">Publishers</h3>
          <div class="space-y-4">
            <div v-for="tier in ['TIER_1', 'TIER_2', 'TIER_3']" :key="tier">
              <h4 class="text-sm font-medium text-gray-500 mb-2">{{ formatTierLabel(tier) }}</h4>
              <ul v-if="groupedPublishers[tier]?.length" class="space-y-1 text-sm">
                <li v-for="name in groupedPublishers[tier]" :key="name">• {{ name }}</li>
              </ul>
              <p v-else class="text-sm text-gray-400 italic">None</p>
            </div>
          </div>
          <p class="mt-4 text-xs text-gray-400">
            {{ systemInfo.entity_tiers.publishers.length }} total
          </p>
        </div>

        <!-- Binders -->
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="text-lg font-semibold mb-4">Binders</h3>
          <div class="space-y-4">
            <div v-for="tier in ['TIER_1', 'TIER_2', 'TIER_3']" :key="tier">
              <h4 class="text-sm font-medium text-gray-500 mb-2">{{ formatTierLabel(tier) }}</h4>
              <ul v-if="groupedBinders[tier]?.length" class="space-y-1 text-sm">
                <li v-for="name in groupedBinders[tier]" :key="name">• {{ name }}</li>
              </ul>
              <p v-else class="text-sm text-gray-400 italic">None</p>
            </div>
          </div>
          <p class="mt-4 text-xs text-gray-400">
            {{ systemInfo.entity_tiers.binders.length }} total
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
```

**Step 2: Run type check**

Run: `npm run type-check`
Expected: No errors

**Step 3: Run lint**

Run: `npm run lint`
Expected: No errors (or auto-fixed)

**Step 4: Commit**

```bash
git add frontend/src/views/AdminConfigView.vue
git commit -m "feat: refactor AdminConfigView to tabbed dashboard"
```

---

## Task 8: Final Integration Test

**Step 1: Run all backend tests**

Run: `poetry run pytest tests/ -q`
Expected: All tests pass

**Step 2: Run frontend checks**

Run: `npm run type-check && npm run lint`
Expected: No errors

**Step 3: Manual verification (if dev server available)**

1. Start backend: `poetry run uvicorn app.main:app --reload`
2. Start frontend: `npm run dev`
3. Login as editor or admin
4. Navigate via Profile dropdown → Config
5. Verify all 4 tabs load and display data

**Step 4: Final commit if any cleanup needed**

---

## Task 9: Create PR

**Step 1: Push branch**

```bash
git push -u origin feat/admin-config-dashboard
```

**Step 2: Create PR targeting staging**

```bash
gh pr create --base staging --title "feat: Admin Config Dashboard with System Status (#529)" --body "## Summary
- Tabbed interface: Settings, System Status, Scoring Config, Entity Tiers
- New endpoint: GET /admin/system-info
- Navigation: Add Config menu item for editors/admins
- Cold start indicator, health badges, key tunables highlighted

## Test Plan
- [ ] Backend tests pass
- [ ] Frontend type-check passes
- [ ] Manual test: all tabs load correctly
- [ ] Manual test: Config menu appears for editors

Closes #529"
```

---

## Summary

| Task | Description | Est. Time |
|------|-------------|-----------|
| 1 | Cold start detection | 5 min |
| 2 | System info endpoint | 15 min |
| 3 | Endpoint tests | 10 min |
| 4 | Router guard | 5 min |
| 5 | NavBar menu item | 5 min |
| 6 | TypeScript types | 5 min |
| 7 | AdminConfigView refactor | 20 min |
| 8 | Integration test | 10 min |
| 9 | Create PR | 5 min |

**Total: ~80 minutes**
