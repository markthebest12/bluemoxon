# Entity Profiles Phase 4 — Production Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 6 open issues blocking entity profile visibility and usability on production: SQS infrastructure (#1597), health check gap (#1599), stale navigation (#1595), navigation discoverability (#1598), timeline range (#1596), and tone CSS refactor (#1590).

**Architecture:** 5 parallel worktree lanes with zero file overlap. Lane E (#1597) is infrastructure investigation — must complete first since it unblocks profile visibility for all other features. Lanes A-D are code changes that can run simultaneously.

**Tech Stack:** Python/FastAPI (backend), Vue 3/TypeScript (frontend), Terraform/AWS (infra), Playwright (E2E), Vitest (unit tests)

---

## Parallel Execution Strategy

### Dependency Graph

```
#1597 (SQS infra) ──────────────────────────> unblocks profile visibility
#1599 (health check)   ─── no deps ──────────> independent
#1596 (timeline range) ─── no deps ──────────> independent
#1595 (view N more) ───────> #1598 (nav UX)   sequential (same file)
#1590 (tone CSS)       ─── no deps ──────────> independent
```

### Worktree Lanes

| Lane | Worktree | Branch | Issues | Files |
|------|----------|--------|--------|-------|
| A | `.tmp/worktrees/fix-timeline` | `fix/ep-timeline-range` | #1596 | `social_circles.py`, `test_social_circles.py` |
| B | `.tmp/worktrees/fix-health` | `fix/ep-health-sqs` | #1599 | `health.py`, `test_health.py` |
| C | `.tmp/worktrees/fix-navigation` | `fix/ep-navigation` | #1595 → #1598 | `SocialCirclesView.vue`, `EdgeSidebar.vue` |
| D | `.tmp/worktrees/fix-tone-css` | `fix/ep-tone-css` | #1590 | `getToneStyle.ts`, `main.css`, `getToneStyle.test.ts` |
| E | main repo | `fix/ep-profile-generation` | #1597 | Terraform, Lambda env, SQS |

### Execution Waves

- **Wave 1:** Launch all 5 lanes in parallel
- **Wave 2:** Merge all branches to staging, run full test suite
- **Wave 3:** Review + E2E validation on staging
- **Wave 4:** Promote staging → main, deploy

---

## Task 1: Fix SQS Profile Generation Infrastructure (#1597)

> **CRITICAL — blocks visibility of all Phase 2+3 features on production**

**Lane:** E (main repo)
**Branch:** `fix/ep-profile-generation`

**Context:** Production has zero generated entity profiles. `POST /entity/profiles/generate-all` returns 500 "Failed to enqueue generation messages". The Terraform code looks correct — the profile-worker module is enabled in both staging and prod tfvars, and the API Lambda gets `BMX_PROFILE_GENERATION_QUEUE_NAME` set from the module output. The issue is likely that Terraform hasn't been applied to production since the profile-worker module was added (PR #1587).

**Files:**
- Check: `infra/terraform/main.tf:655-713` (profile_worker module block)
- Check: `infra/terraform/main.tf:415` (BMX_PROFILE_GENERATION_QUEUE_NAME env var for API Lambda)
- Check: `infra/terraform/envs/prod.tfvars:57` (`enable_profile_worker = true`)

**Step 1: Check current Terraform state for production**

```bash
cd infra/terraform
AWS_PROFILE=bmx-prod terraform plan -var-file=envs/prod.tfvars 2>&1 | head -100
```

Look for:
- `module.profile_worker[0]` resources (SQS queue, Lambda, IAM role)
- If they show as "to be created" → Terraform hasn't been applied
- If they exist → the issue is something else (env var, IAM, etc.)

**Step 2: If Terraform needs applying**

```bash
AWS_PROFILE=bmx-prod terraform apply -var-file=envs/prod.tfvars
```

**Step 3: If Terraform is already applied, check Lambda env vars**

```bash
bmx-api --prod GET /health/deep
```

Look at the SQS section. Also verify the API Lambda has the queue name set:

```bash
AWS_PROFILE=bmx-prod aws lambda get-function-configuration --function-name bluemoxon-api --query "Environment.Variables.BMX_PROFILE_GENERATION_QUEUE_NAME" --output text
```

**Step 4: If queue exists and env var is set, check IAM permissions**

Look at CloudWatch logs for the API Lambda around the time of the 500 error:

```bash
AWS_PROFILE=bmx-prod aws logs filter-log-events --log-group-name /aws/lambda/bluemoxon-api --filter-pattern "profile" --start-time $(date -v-1H +%s000) --limit 20
```

**Step 5: Once infrastructure is working, trigger batch generation**

```bash
bmx-api --prod POST /entity/profiles/generate-all
```

Expected: 200 response with number of jobs enqueued.

**Step 6: Verify profiles populate**

Wait a few minutes for Lambda to process, then:

```bash
bmx-api --prod GET /entity/profiles/author/31
```

Expected: `bio_summary` is non-null, `generated_at` has a timestamp.

**Step 7: Commit any Terraform changes if needed**

```bash
git add infra/terraform/
git commit -m "fix: deploy profile-worker infrastructure to production (#1597)"
```

---

## Task 2: Add Profile Generation Queue to Deep Health Check (#1599)

**Lane:** B (`.tmp/worktrees/fix-health`)
**Branch:** `fix/ep-health-sqs`

**Files:**
- Modify: `backend/app/api/v1/health.py:180-184`
- Modify: `backend/tests/test_health.py`

**Step 1: Write the failing test**

In `backend/tests/test_health.py`, add a test class for the profile generation queue in `check_sqs()`. The existing test at line 49-72 validates the deep health endpoint structure, but there are no dedicated `check_sqs()` tests.

Add at the end of the file:

```python
class TestCheckSqsProfileGeneration:
    """Tests for profile generation queue in SQS health check."""

    def test_check_sqs_includes_profile_generation_queue(self, monkeypatch):
        """check_sqs should include profile_generation when configured."""
        from app.api.v1.health import check_sqs
        from app.core.config import settings

        monkeypatch.setattr(settings, "profile_generation_queue_name", "test-profile-gen-queue")
        monkeypatch.setattr(settings, "analysis_queue_name", None)
        monkeypatch.setattr(settings, "eval_runbook_queue_name", None)
        monkeypatch.setattr(settings, "image_processing_queue_name", None)

        # Mock boto3 SQS client
        import unittest.mock as mock

        mock_sqs = mock.MagicMock()
        mock_sqs.get_queue_url.return_value = {"QueueUrl": "https://sqs.us-east-1.amazonaws.com/123/test-profile-gen-queue"}
        mock_sqs.get_queue_attributes.return_value = {
            "Attributes": {"ApproximateNumberOfMessages": "5"}
        }
        monkeypatch.setattr("app.api.v1.health.boto3.client", lambda *a, **kw: mock_sqs)

        result = check_sqs()

        assert result["status"] == "healthy"
        assert "profile_generation" in result["queues"]
        assert result["queues"]["profile_generation"]["status"] == "healthy"
        assert result["queues"]["profile_generation"]["messages"] == 5
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/mark/projects/bluemoxon
poetry run pytest backend/tests/test_health.py::TestCheckSqsProfileGeneration -v
```

Expected: FAIL — `"profile_generation" not in result["queues"]` because the queue isn't in the dict yet.

**Step 3: Write the implementation**

In `backend/app/api/v1/health.py`, modify the `queues` dict at line 180-184:

Change from:
```python
    queues = {
        "analysis": settings.analysis_queue_name,
        "eval_runbook": settings.eval_runbook_queue_name,
        "image_processing": settings.image_processing_queue_name,
    }
```

To:
```python
    queues = {
        "analysis": settings.analysis_queue_name,
        "eval_runbook": settings.eval_runbook_queue_name,
        "image_processing": settings.image_processing_queue_name,
        "profile_generation": settings.profile_generation_queue_name,
    }
```

That's it. The rest of the check logic (filter to configured, get URL, get attributes) handles it automatically.

**Step 4: Run test to verify it passes**

```bash
poetry run pytest backend/tests/test_health.py::TestCheckSqsProfileGeneration -v
```

Expected: PASS

**Step 5: Run full health test suite**

```bash
poetry run pytest backend/tests/test_health.py -v
```

Expected: All pass, no regressions.

**Step 6: Commit**

```bash
git add backend/app/api/v1/health.py backend/tests/test_health.py
git commit -m "feat: add profile generation queue to deep health check (#1599)"
```

---

## Task 3: Fix Timeline Range Dynamic Clamping (#1596)

**Lane:** A (`.tmp/worktrees/fix-timeline`)
**Branch:** `fix/ep-timeline-range`

**Files:**
- Modify: `backend/app/services/social_circles.py:32-35` (constants) and `293-304` (date_range calc)
- Modify: `backend/tests/api/v1/test_social_circles.py`

**Context:** The backend calculates `date_range` from raw `min()/max()` of all author `birth_year`/`death_year`. An author with `birth_year=1265` causes the range to span 1265-1967. The fix adds IQR-based outlier filtering to produce a reasonable range while keeping the default fallback.

**Step 1: Write the failing tests**

In `backend/tests/api/v1/test_social_circles.py`, add a test class. First, find the imports at the top of the file. The test needs to test the `_clamp_date_range` helper directly. Add:

```python
class TestDateRangeClamping:
    """Tests for date range calculation with outlier filtering."""

    def test_normal_years_unchanged(self):
        """Victorian-era years should produce a tight range."""
        from app.services.social_circles import _compute_date_range

        years = [1810, 1820, 1830, 1840, 1850, 1860, 1870, 1880, 1890, 1900]
        result = _compute_date_range(years)
        assert result == (1810, 1900)

    def test_outlier_year_excluded(self):
        """A single extreme outlier (1265) should be excluded."""
        from app.services.social_circles import _compute_date_range

        years = [1265, 1810, 1820, 1830, 1840, 1850, 1860, 1870, 1880, 1900, 1967]
        result = _compute_date_range(years)
        # 1265 should be excluded as outlier; 1967 is within reasonable range
        assert result[0] >= 1700
        assert result[1] <= 2025

    def test_empty_years_returns_default(self):
        """Empty years list returns DEFAULT_DATE_RANGE."""
        from app.services.social_circles import _compute_date_range, DEFAULT_DATE_RANGE

        result = _compute_date_range([])
        assert result == DEFAULT_DATE_RANGE

    def test_single_year(self):
        """A single year should work without error."""
        from app.services.social_circles import _compute_date_range

        result = _compute_date_range([1850])
        assert result == (1850, 1850)

    def test_all_outliers_returns_default(self):
        """If ALL years are outside reasonable bounds, return default."""
        from app.services.social_circles import _compute_date_range, DEFAULT_DATE_RANGE

        result = _compute_date_range([500, 600, 700])
        assert result == DEFAULT_DATE_RANGE
```

**Step 2: Run tests to verify they fail**

```bash
cd /Users/mark/projects/bluemoxon
poetry run pytest backend/tests/api/v1/test_social_circles.py::TestDateRangeClamping -v
```

Expected: FAIL — `_compute_date_range` does not exist yet.

**Step 3: Write the implementation**

In `backend/app/services/social_circles.py`, add constants after `DEFAULT_DATE_RANGE` (line 35):

```python
# Reasonable year bounds for clamping outliers in date range calculation.
# Authors with birth/death years outside this range are likely data errors.
REASONABLE_MIN_YEAR = 1700
REASONABLE_MAX_YEAR = 2025
```

Add the new function after the constants (before `build_social_circles_graph`):

```python
def _compute_date_range(years: list[int]) -> tuple[int, int]:
    """Compute date range from years, filtering outliers outside reasonable bounds."""
    if not years:
        return DEFAULT_DATE_RANGE

    reasonable = [y for y in years if REASONABLE_MIN_YEAR <= y <= REASONABLE_MAX_YEAR]
    if not reasonable:
        return DEFAULT_DATE_RANGE

    return (min(reasonable), max(reasonable))
```

Then replace the inline date_range calculation at lines 293-304. Change from:

```python
    # Calculate date range
    years = []
    for node in nodes.values():
        if node.birth_year:
            years.append(node.birth_year)
        if node.death_year:
            years.append(node.death_year)

    date_range = (
        min(years) if years else DEFAULT_DATE_RANGE[0],
        max(years) if years else DEFAULT_DATE_RANGE[1],
    )
```

To:

```python
    # Calculate date range (with outlier filtering)
    years: list[int] = []
    for node in nodes.values():
        if node.birth_year:
            years.append(node.birth_year)
        if node.death_year:
            years.append(node.death_year)

    date_range = _compute_date_range(years)
```

**Step 4: Run tests to verify they pass**

```bash
poetry run pytest backend/tests/api/v1/test_social_circles.py::TestDateRangeClamping -v
```

Expected: All 5 PASS.

**Step 5: Run full social circles test suite**

```bash
poetry run pytest backend/tests/api/v1/test_social_circles.py -v
```

Expected: All pass, no regressions.

**Step 6: Lint**

```bash
poetry run ruff check backend/app/services/social_circles.py
poetry run ruff format --check backend/app/services/social_circles.py
```

**Step 7: Commit**

```bash
git add backend/app/services/social_circles.py backend/tests/api/v1/test_social_circles.py
git commit -m "fix: clamp social circles timeline range to reasonable year bounds (#1596)"
```

---

## Task 4: Fix "View N More" Navigation (#1595)

**Lane:** C (`.tmp/worktrees/fix-navigation`)
**Branch:** `fix/ep-navigation`

**Files:**
- Modify: `frontend/src/views/SocialCirclesView.vue:493-499` (handleViewProfile function)

**Context:** `handleViewProfile(_nodeId: NodeId)` currently shows a "coming soon" toast. Entity profiles have shipped. The function needs to look up the node from the existing `nodeMap` computed property (line 390-396) and navigate via `router.push`. The `useRouter` import is not present — it needs to be added.

**Step 1: Add the router import**

In `frontend/src/views/SocialCirclesView.vue`, add `useRouter` to the vue-router import. Find the existing import (around line 2-12). There's a commented-out note about useRouter. Add it to the imports from `vue-router`:

```typescript
import { useRouter } from "vue-router";
```

And after the existing const declarations, add:

```typescript
const router = useRouter();
```

**Step 2: Replace handleViewProfile**

Change the function at lines 493-499 from:

```typescript
function handleViewProfile(_nodeId: NodeId) {
  // TODO: Navigate to entity detail page when route exists
  // void router.push({ name: "entity-detail", params: { id: nodeId } });
  showToastMessage("Entity profiles coming soon");
}
```

To:

```typescript
function handleViewProfile(nodeId: NodeId) {
  const node = nodeMap.value.get(nodeId);
  if (node?.entity_id && node?.type) {
    void router.push({
      name: "entity-profile",
      params: { type: node.type, id: String(node.entity_id) },
    });
  }
}
```

Key details:
- `nodeMap` is the computed `Map<string, ApiNode>` at line 390-396 — O(1) lookup
- Route name is `"entity-profile"` (defined in `frontend/src/router/index.ts:100-106`)
- `entity_id` is a number, must be `String()` for route params
- `node.type` is `"author" | "publisher" | "binder"`

**Step 3: Remove stale comments**

Delete any `// Note: useRouter from "vue-router" will be needed when entity-detail route is implemented` comments (around line 12 and line 134).

**Step 4: Type-check and lint**

```bash
npm run --prefix frontend type-check
npm run --prefix frontend lint
npm run --prefix frontend format
```

**Step 5: Commit**

```bash
git add frontend/src/views/SocialCirclesView.vue
git commit -m "fix: navigate to entity profile from 'View N more' link (#1595)"
```

---

## Task 5: Add Profile Links to EdgeSidebar (#1598)

**Lane:** C (same worktree as Task 4, runs after it)
**Branch:** `fix/ep-navigation` (same branch)

**Files:**
- Modify: `frontend/src/components/socialcircles/EdgeSidebar.vue:325-333` (footer)

**Context:** EdgeSidebar shows a connection between two entities. The footer has "View Author" / "View Publisher" buttons that emit `selectNode` (which selects the node on the graph). We want to also add "View Profile" links that navigate to the entity profile page. Both source and target nodes have `entity_id` and `type` available via computed properties `sourceNode` and `targetNode`.

**Step 1: Add router-link imports**

In `EdgeSidebar.vue`, check if `router-link` is available (it should be since Vue Router is installed globally). No additional import needed for `<router-link>` in the template.

**Step 2: Add profile links to the footer**

In `frontend/src/components/socialcircles/EdgeSidebar.vue`, modify the footer section at lines 325-333. Change from:

```vue
<footer class="edge-sidebar__footer">
  <button class="edge-sidebar__view-button" @click="emit('selectNode', sourceNode.id)">
    View {{ TYPE_LABELS[sourceNode.type] || sourceNode.type }}
  </button>
  <button class="edge-sidebar__view-button" @click="emit('selectNode', targetNode.id)">
    View {{ TYPE_LABELS[targetNode.type] || targetNode.type }}
  </button>
</footer>
```

To:

```vue
<footer class="edge-sidebar__footer">
  <div class="edge-sidebar__footer-group">
    <button class="edge-sidebar__view-button" @click="emit('selectNode', sourceNode.id)">
      View {{ TYPE_LABELS[sourceNode.type] || sourceNode.type }}
    </button>
    <router-link
      :to="{ name: 'entity-profile', params: { type: sourceNode.type, id: String(sourceNode.entity_id) } }"
      class="edge-sidebar__profile-link"
    >
      Profile &rarr;
    </router-link>
  </div>
  <div class="edge-sidebar__footer-group">
    <button class="edge-sidebar__view-button" @click="emit('selectNode', targetNode.id)">
      View {{ TYPE_LABELS[targetNode.type] || targetNode.type }}
    </button>
    <router-link
      :to="{ name: 'entity-profile', params: { type: targetNode.type, id: String(targetNode.entity_id) } }"
      class="edge-sidebar__profile-link"
    >
      Profile &rarr;
    </router-link>
  </div>
</footer>
```

**Step 3: Add CSS for the new elements**

In the `<style scoped>` section of `EdgeSidebar.vue`, add:

```css
.edge-sidebar__footer-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.edge-sidebar__profile-link {
  color: var(--color-accent-gold, #b8860b);
  font-size: 13px;
  text-decoration: none;
}

.edge-sidebar__profile-link:hover {
  text-decoration: underline;
}
```

**Step 4: Type-check and lint**

```bash
npm run --prefix frontend type-check
npm run --prefix frontend lint
npm run --prefix frontend format
```

**Step 5: Commit**

```bash
git add frontend/src/components/socialcircles/EdgeSidebar.vue
git commit -m "feat: add entity profile links to EdgeSidebar footer (#1598)"
```

---

## Task 6: Move Tone Colors to CSS Custom Properties (#1590)

**Lane:** D (`.tmp/worktrees/fix-tone-css`)
**Branch:** `fix/ep-tone-css`

**Files:**
- Modify: `frontend/src/assets/main.css` (add tone custom properties inside `@theme` block, before line 136)
- Modify: `frontend/src/composables/entityprofile/getToneStyle.ts` (return `var()` references)
- Modify: `frontend/src/composables/entityprofile/__tests__/getToneStyle.test.ts` (update assertions)

**Context:** `getToneStyle()` currently returns hardcoded hex colors (`#c0392b`, etc.) as inline `borderLeftColor` styles. These bypass the CSS custom property system. The fix defines `--color-tone-*` properties in `main.css` and returns `var(--color-tone-*)` from the function so theming can override them.

**Step 1: Update the test expectations**

In `frontend/src/composables/entityprofile/__tests__/getToneStyle.test.ts`, update the tests to expect CSS variable references instead of hex colors:

```typescript
import { describe, it, expect } from "vitest";
import { getToneStyle } from "../getToneStyle";
import type { Tone } from "@/types/entityProfile";

describe("getToneStyle", () => {
  const ALL_TONES: Tone[] = ["dramatic", "scandalous", "tragic", "intellectual", "triumphant"];

  it("returns a className and color for each tone", () => {
    for (const tone of ALL_TONES) {
      const style = getToneStyle(tone);
      expect(style.className).toBe(`tone--${tone}`);
      expect(style.color).toBe(`var(--color-tone-${tone})`);
    }
  });

  it("returns distinct colors for each tone", () => {
    const colors = ALL_TONES.map((t) => getToneStyle(t).color);
    expect(new Set(colors).size).toBe(ALL_TONES.length);
  });

  it("returns fallback for unknown tone", () => {
    const style = getToneStyle("unknown" as Tone);
    expect(style.className).toBe("tone--unknown");
    expect(style.color).toBe("var(--color-tone-unknown, #b8860b)");
  });
});
```

**Step 2: Run test to verify it fails**

```bash
npm run --prefix frontend test -- --run src/composables/entityprofile/__tests__/getToneStyle.test.ts
```

Expected: FAIL — current function returns hex values like `#c0392b`, not `var(--color-tone-dramatic)`.

**Step 3: Add CSS custom properties to main.css**

In `frontend/src/assets/main.css`, add tone color tokens inside the `@theme` block, before the closing `}` at line 136. Insert after the status tokens section (after line 135):

```css
  /* ============================================
     TONE TOKENS - Entity profile narrative tones
     ============================================ */
  --color-tone-dramatic: #c0392b;
  --color-tone-scandalous: #e74c3c;
  --color-tone-tragic: #7f8c8d;
  --color-tone-intellectual: #2c3e50;
  --color-tone-triumphant: #d4a017;
```

**Step 4: Update getToneStyle to return var() references**

Replace the full contents of `frontend/src/composables/entityprofile/getToneStyle.ts`:

```typescript
import type { Tone } from "@/types/entityProfile";

export interface ToneStyle {
  className: string;
  color: string;
}

const KNOWN_TONES = new Set(["dramatic", "scandalous", "tragic", "intellectual", "triumphant"]);

const FALLBACK_COLOR = "#b8860b";

export function getToneStyle(tone: Tone): ToneStyle {
  const isKnown = KNOWN_TONES.has(tone);
  return {
    className: `tone--${tone}`,
    color: isKnown ? `var(--color-tone-${tone})` : `var(--color-tone-${tone}, ${FALLBACK_COLOR})`,
  };
}
```

Key changes:
- `TONE_COLORS` hex map removed — colors now live in CSS
- Known tones use `var(--color-tone-dramatic)` etc.
- Unknown tones use `var(--color-tone-unknown, #b8860b)` with inline fallback
- `KNOWN_TONES` Set for O(1) lookup

**Step 5: Run test to verify it passes**

```bash
npm run --prefix frontend test -- --run src/composables/entityprofile/__tests__/getToneStyle.test.ts
```

Expected: All 3 PASS.

**Step 6: Run full frontend test suite**

```bash
npm run --prefix frontend test -- --run
```

Expected: All pass, no regressions. The `ConnectionGossipPanel.test.ts` and other component tests should still pass since they mount the real component and `var()` values are valid CSS (jsdom won't resolve them but border styles are just strings).

**Step 7: Lint and format**

```bash
npm run --prefix frontend lint
npm run --prefix frontend format
```

**Step 8: Commit**

```bash
git add frontend/src/assets/main.css frontend/src/composables/entityprofile/getToneStyle.ts frontend/src/composables/entityprofile/__tests__/getToneStyle.test.ts
git commit -m "feat: move tone colors to CSS custom properties for theming (#1590)"
```

---

## Wave 2: Merge to Staging

After all lanes complete, merge each branch to staging:

```bash
# For each branch:
gh pr create --base staging --head fix/ep-timeline-range --title "fix: clamp timeline range to reasonable year bounds (#1596)"
gh pr create --base staging --head fix/ep-health-sqs --title "feat: add profile generation queue to health check (#1599)"
gh pr create --base staging --head fix/ep-navigation --title "fix: entity profile navigation from social circles (#1595, #1598)"
gh pr create --base staging --head fix/ep-tone-css --title "feat: move tone colors to CSS custom properties (#1590)"
gh pr create --base staging --head fix/ep-profile-generation --title "fix: deploy profile-worker infrastructure (#1597)"
```

Merge each with `--squash`.

## Wave 3: Staging Validation

Run full validation:

```bash
# Backend
poetry run ruff check backend/
poetry run ruff format --check backend/
poetry run pytest backend/ -v

# Frontend
npm run --prefix frontend lint
npm run --prefix frontend format
npm run --prefix frontend type-check
npm run --prefix frontend test -- --run

# E2E against staging
npm run --prefix frontend e2e
```

Verify on staging:
1. `/health/deep` shows `profile_generation` queue as healthy
2. Social circles timeline range is reasonable (no 1265)
3. "View N more" link navigates to entity profile
4. EdgeSidebar footer has "Profile" links
5. Entity profile pages show generated content (bio, stories, gossip)

## Wave 4: Ship

```bash
gh pr create --base main --head staging --title "chore: Promote staging"
gh pr merge <n> --merge
gh run watch <id> --exit-status
```
