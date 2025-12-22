# Admin Cost Tab Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a Cost tab to the Admin Config Dashboard showing Bedrock usage costs by model with usage descriptions.

**Architecture:** New `/admin/costs` endpoint fetches AWS Cost Explorer data, caches for 1 hour, returns structured cost breakdown. Frontend displays in new tab with table and simple bar chart.

**Tech Stack:** AWS Cost Explorer API (boto3), FastAPI, Vue 3, TypeScript

---

## Task 1: Add Cost Explorer IAM Permission to Lambda Module

**Files:**
- Modify: `infra/terraform/modules/lambda/variables.tf`
- Modify: `infra/terraform/modules/lambda/main.tf`

**Step 1: Add variable for Cost Explorer access**

Add to `infra/terraform/modules/lambda/variables.tf` at line 1 (before existing variables):

```hcl
variable "cost_explorer_access" {
  type        = bool
  description = "Grant ce:GetCostAndUsage permission for AWS Cost Explorer"
  default     = false
}
```

**Step 2: Add IAM policy for Cost Explorer**

Add to `infra/terraform/modules/lambda/main.tf` after the `bedrock_access` policy (around line 232):

```hcl
# Cost Explorer access for admin cost dashboard
resource "aws_iam_role_policy" "cost_explorer_access" {
  count = var.cost_explorer_access ? 1 : 0
  name  = "cost-explorer-access"
  role  = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ce:GetCostAndUsage"]
        Resource = "*"
      }
    ]
  })
}
```

**Step 3: Commit**

```bash
git add infra/terraform/modules/lambda/variables.tf infra/terraform/modules/lambda/main.tf
git commit -m "feat: add Cost Explorer IAM permission to Lambda module"
```

---

## Task 2: Enable Cost Explorer for API Lambda

**Files:**
- Modify: `infra/terraform/main.tf`

**Step 1: Find the API Lambda module call and add cost_explorer_access**

Search for `module "api_lambda"` in `infra/terraform/main.tf` and add:

```hcl
cost_explorer_access = true
```

**Step 2: Commit**

```bash
git add infra/terraform/main.tf
git commit -m "feat: enable Cost Explorer access for API Lambda"
```

---

## Task 3: Create Cost Explorer Service

**Files:**
- Create: `backend/app/services/cost_explorer.py`

**Step 1: Create the service file**

Create `backend/app/services/cost_explorer.py`:

```python
"""AWS Cost Explorer service for retrieving Bedrock costs."""

from datetime import UTC, datetime, timedelta
from typing import Any

import boto3
from botocore.exceptions import ClientError

from app.services.bedrock import MODEL_USAGE

# Cache for cost data (simple in-memory cache)
_cost_cache: dict[str, Any] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour

# Map AWS service names to our model names
AWS_SERVICE_TO_MODEL = {
    "Claude Sonnet 4.5 (Amazon Bedrock Edition)": "Sonnet 4.5",
    "Claude Opus 4.5 (Amazon Bedrock Edition)": "Opus 4.5",
    "Claude 3 Haiku (Amazon Bedrock Edition)": "Haiku 3",
    "Claude 3.5 Sonnet (Amazon Bedrock Edition)": "Sonnet 3.5",
    "Claude 3.5 Sonnet v2 (Amazon Bedrock Edition)": "Sonnet 3.5 v2",
}

# Model name to usage description mapping
MODEL_USAGE_DESCRIPTIONS = {
    "Sonnet 4.5": MODEL_USAGE.get("sonnet", "Primary analysis"),
    "Opus 4.5": MODEL_USAGE.get("opus", "High quality analysis"),
    "Haiku 3": MODEL_USAGE.get("haiku", "Fast extraction"),
    "Sonnet 3.5": "Legacy analysis",
    "Sonnet 3.5 v2": "Legacy analysis",
}

# Other AWS services to track
OTHER_SERVICES = [
    "AWS Lambda",
    "Amazon Relational Database Service",
    "Amazon Virtual Private Cloud",
    "Amazon Simple Storage Service",
    "Amazon CloudFront",
    "Amazon API Gateway",
    "EC2 - Other",
]


def _get_cache_key() -> str:
    """Generate cache key based on current month."""
    now = datetime.now(UTC)
    return f"costs_{now.year}_{now.month}"


def _is_cache_valid() -> bool:
    """Check if cache is still valid."""
    cache_key = _get_cache_key()
    if cache_key not in _cost_cache:
        return False
    cached_at = _cost_cache[cache_key].get("cached_at")
    if not cached_at:
        return False
    age = (datetime.now(UTC) - datetime.fromisoformat(cached_at)).total_seconds()
    return age < CACHE_TTL_SECONDS


def get_costs() -> dict[str, Any]:
    """Get cost data from AWS Cost Explorer.

    Returns cached data if available and fresh, otherwise fetches from AWS.
    """
    cache_key = _get_cache_key()

    if _is_cache_valid():
        return _cost_cache[cache_key]

    try:
        costs = _fetch_costs_from_aws()
        _cost_cache[cache_key] = costs
        return costs
    except ClientError as e:
        # Return error response, cache for 5 minutes to avoid hammering
        error_response = {
            "error": str(e),
            "cached_at": datetime.now(UTC).isoformat(),
            "period_start": "",
            "period_end": "",
            "bedrock_models": [],
            "bedrock_total": 0.0,
            "daily_trend": [],
            "other_costs": {},
            "total_aws_cost": 0.0,
        }
        _cost_cache[cache_key] = error_response
        return error_response


def _fetch_costs_from_aws() -> dict[str, Any]:
    """Fetch cost data from AWS Cost Explorer."""
    client = boto3.client("ce", region_name="us-east-1")  # CE is only in us-east-1

    now = datetime.now(UTC)
    period_start = now.replace(day=1).strftime("%Y-%m-%d")
    period_end = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    # Get monthly costs grouped by service
    monthly_response = client.get_cost_and_usage(
        TimePeriod={"Start": period_start, "End": period_end},
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
    )

    # Get daily costs for trend (last 14 days)
    trend_start = (now - timedelta(days=14)).strftime("%Y-%m-%d")
    daily_response = client.get_cost_and_usage(
        TimePeriod={"Start": trend_start, "End": period_end},
        Granularity="DAILY",
        Metrics=["UnblendedCost"],
        Filter={
            "Dimensions": {
                "Key": "SERVICE",
                "Values": list(AWS_SERVICE_TO_MODEL.keys()),
            }
        },
    )

    # Parse monthly costs
    bedrock_models = []
    other_costs = {}
    total_aws_cost = 0.0

    for result in monthly_response.get("ResultsByTime", []):
        for group in result.get("Groups", []):
            service_name = group["Keys"][0]
            cost = float(group["Metrics"]["UnblendedCost"]["Amount"])
            total_aws_cost += cost

            if service_name in AWS_SERVICE_TO_MODEL:
                model_name = AWS_SERVICE_TO_MODEL[service_name]
                bedrock_models.append({
                    "model_name": model_name,
                    "usage": MODEL_USAGE_DESCRIPTIONS.get(model_name, ""),
                    "mtd_cost": round(cost, 2),
                })
            elif service_name in OTHER_SERVICES:
                # Shorten service names
                short_name = (
                    service_name.replace("Amazon ", "")
                    .replace("AWS ", "")
                    .replace(" Service", "")
                )
                other_costs[short_name] = round(cost, 2)

    # Sort bedrock models by cost descending
    bedrock_models.sort(key=lambda x: x["mtd_cost"], reverse=True)
    bedrock_total = sum(m["mtd_cost"] for m in bedrock_models)

    # Parse daily trend
    daily_trend = []
    for result in daily_response.get("ResultsByTime", []):
        date = result["TimePeriod"]["Start"]
        cost = float(result.get("Total", {}).get("UnblendedCost", {}).get("Amount", 0))
        if cost > 0:
            daily_trend.append({"date": date, "cost": round(cost, 2)})

    return {
        "period_start": period_start,
        "period_end": period_end,
        "bedrock_models": bedrock_models,
        "bedrock_total": round(bedrock_total, 2),
        "daily_trend": daily_trend,
        "other_costs": other_costs,
        "total_aws_cost": round(total_aws_cost, 2),
        "cached_at": datetime.now(UTC).isoformat(),
    }
```

**Step 2: Run lint to verify**

Run: `cd backend && poetry run ruff check app/services/cost_explorer.py`
Expected: All checks passed!

**Step 3: Commit**

```bash
git add backend/app/services/cost_explorer.py
git commit -m "feat: add Cost Explorer service for Bedrock cost tracking"
```

---

## Task 4: Add Cost Endpoint to Admin API

**Files:**
- Modify: `backend/app/api/v1/admin.py`

**Step 1: Add Pydantic models for cost response**

Add after `LimitsConfig` class (around line 124) in `backend/app/api/v1/admin.py`:

```python
class BedrockModelCost(BaseModel):
    """Cost for a single Bedrock model."""

    model_name: str
    usage: str
    mtd_cost: float


class DailyCost(BaseModel):
    """Daily cost data point."""

    date: str
    cost: float


class CostResponse(BaseModel):
    """Cost data response."""

    period_start: str
    period_end: str
    bedrock_models: list[BedrockModelCost]
    bedrock_total: float
    daily_trend: list[DailyCost]
    other_costs: dict[str, float]
    total_aws_cost: float
    cached_at: str
    error: str | None = None
```

**Step 2: Add the /costs endpoint**

Add after the `get_system_info` function (at the end of the file):

```python
@router.get("/costs", response_model=CostResponse)
def get_costs():
    """Get AWS cost data for admin dashboard.

    Returns Bedrock model costs with usage descriptions,
    daily trend, and other AWS service costs.
    Cached for 1 hour.
    """
    from app.services.cost_explorer import get_costs as fetch_costs

    return CostResponse(**fetch_costs())
```

**Step 3: Run lint to verify**

Run: `cd backend && poetry run ruff check app/api/v1/admin.py`
Expected: All checks passed!

**Step 4: Commit**

```bash
git add backend/app/api/v1/admin.py
git commit -m "feat: add /admin/costs endpoint for cost dashboard"
```

---

## Task 5: Add TypeScript Types for Cost Tab

**Files:**
- Modify: `frontend/src/types/admin.ts`

**Step 1: Add cost types**

Add at end of `frontend/src/types/admin.ts`:

```typescript
export interface BedrockModelCost {
  model_name: string;
  usage: string;
  mtd_cost: number;
}

export interface DailyCost {
  date: string;
  cost: number;
}

export interface CostResponse {
  period_start: string;
  period_end: string;
  bedrock_models: BedrockModelCost[];
  bedrock_total: number;
  daily_trend: DailyCost[];
  other_costs: Record<string, number>;
  total_aws_cost: number;
  cached_at: string;
  error?: string;
}
```

**Step 2: Run type-check**

Run: `cd frontend && npm run type-check`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/types/admin.ts
git commit -m "feat: add TypeScript types for cost response"
```

---

## Task 6: Add Cost Tab to Frontend

**Files:**
- Modify: `frontend/src/views/AdminConfigView.vue`

**Step 1: Add cost data ref and fetch function**

In the `<script setup>` section, after the existing refs (around line 20), add:

```typescript
import type { CostResponse } from '@/types/admin';

const costData = ref<CostResponse | null>(null);
const costLoading = ref(false);
const costError = ref<string | null>(null);

async function fetchCostData() {
  costLoading.value = true;
  costError.value = null;
  try {
    const response = await fetch(`${import.meta.env.VITE_API_URL}/admin/costs`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
      },
    });
    if (!response.ok) throw new Error('Failed to fetch cost data');
    costData.value = await response.json();
    if (costData.value?.error) {
      costError.value = costData.value.error;
    }
  } catch (e) {
    costError.value = e instanceof Error ? e.message : 'Unknown error';
  } finally {
    costLoading.value = false;
  }
}
```

**Step 2: Add formatCurrency helper**

Add after the existing helper functions:

```typescript
function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function getBarWidth(cost: number, maxCost: number): string {
  if (maxCost === 0) return '0%';
  return `${(cost / maxCost) * 100}%`;
}
```

**Step 3: Add Cost tab button**

Find the tab buttons section and add a 4th tab:

```html
<button
  :class="['tab-button', { active: activeTab === 'cost' }]"
  @click="activeTab = 'cost'; if (!costData) fetchCostData();"
>
  Cost
</button>
```

**Step 4: Add Cost tab content**

Add after the Tiered Entities tab content section:

```html
<!-- Cost Tab -->
<div v-if="activeTab === 'cost'" class="tab-content">
  <div v-if="costLoading" class="loading">Loading cost data...</div>
  <div v-else-if="costError" class="error-message">
    Cost data unavailable: {{ costError }}
  </div>
  <div v-else-if="costData">
    <!-- Bedrock Costs -->
    <div class="config-section">
      <h3>Bedrock Usage Costs ({{ new Date(costData.period_start).toLocaleDateString('en-US', { month: 'long', year: 'numeric' }) }})</h3>
      <table class="config-table">
        <thead>
          <tr>
            <th>Model</th>
            <th>Usage</th>
            <th class="text-right">MTD Cost</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="model in costData.bedrock_models" :key="model.model_name">
            <td><strong>{{ model.model_name }}</strong></td>
            <td class="usage-desc">{{ model.usage }}</td>
            <td class="text-right">{{ formatCurrency(model.mtd_cost) }}</td>
          </tr>
          <tr class="total-row">
            <td><strong>Total Bedrock</strong></td>
            <td></td>
            <td class="text-right"><strong>{{ formatCurrency(costData.bedrock_total) }}</strong></td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Daily Trend -->
    <div class="config-section" v-if="costData.daily_trend.length > 0">
      <h3>Daily Trend (Last 14 Days)</h3>
      <div class="daily-trend">
        <div
          v-for="day in costData.daily_trend"
          :key="day.date"
          class="trend-row"
        >
          <span class="trend-date">{{ formatDate(day.date) }}</span>
          <div class="trend-bar-container">
            <div
              class="trend-bar"
              :style="{ width: getBarWidth(day.cost, Math.max(...costData.daily_trend.map(d => d.cost))) }"
            ></div>
          </div>
          <span class="trend-cost">{{ formatCurrency(day.cost) }}</span>
        </div>
      </div>
    </div>

    <!-- Other AWS Costs -->
    <details class="config-section">
      <summary><h3 style="display: inline;">Other AWS Costs</h3></summary>
      <div class="other-costs">
        <div v-for="(cost, service) in costData.other_costs" :key="service" class="other-cost-item">
          <span>{{ service }}</span>
          <span>{{ formatCurrency(cost) }}</span>
        </div>
        <div class="other-cost-item total-row">
          <span><strong>Total AWS</strong></span>
          <span><strong>{{ formatCurrency(costData.total_aws_cost) }}</strong></span>
        </div>
      </div>
    </details>

    <!-- Cache indicator -->
    <div class="cache-indicator">
      Last updated: {{ new Date(costData.cached_at).toLocaleString() }} (cached 1hr)
    </div>
  </div>
</div>
```

**Step 5: Add CSS styles**

Add to the `<style scoped>` section:

```css
.usage-desc {
  color: #666;
  font-size: 0.9em;
}

.total-row {
  border-top: 2px solid #ddd;
  background-color: #f9f9f9;
}

.text-right {
  text-align: right;
}

.daily-trend {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.trend-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.trend-date {
  width: 60px;
  font-size: 0.85em;
  color: #666;
}

.trend-bar-container {
  flex: 1;
  height: 20px;
  background-color: #eee;
  border-radius: 4px;
  overflow: hidden;
}

.trend-bar {
  height: 100%;
  background-color: #4a90d9;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.trend-cost {
  width: 70px;
  text-align: right;
  font-size: 0.85em;
}

.other-costs {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 0;
}

.other-cost-item {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
}

.cache-indicator {
  margin-top: 20px;
  font-size: 0.8em;
  color: #888;
  text-align: right;
}

details summary {
  cursor: pointer;
  padding: 8px 0;
}

details summary h3 {
  margin: 0;
}
```

**Step 6: Run lint and type-check**

Run: `cd frontend && npm run lint`
Expected: No errors

Run: `cd frontend && npm run type-check`
Expected: No errors

**Step 7: Commit**

```bash
git add frontend/src/views/AdminConfigView.vue
git commit -m "feat: add Cost tab to admin dashboard"
```

---

## Task 7: Run Full Validation and Create PR

**Step 1: Run backend validation**

Run: `cd backend && poetry run ruff check .`
Expected: All checks passed!

Run: `cd backend && poetry run ruff format --check .`
Expected: All files already formatted

**Step 2: Run frontend validation**

Run: `cd frontend && npm run lint`
Expected: No errors

Run: `cd frontend && npm run type-check`
Expected: No errors

**Step 3: Push and create PR**

```bash
git push -u origin feat/admin-cost-tab
```

Create PR:
```bash
gh pr create --base staging --title "feat: Add Cost tab to admin dashboard" --body "## Summary
- Add AWS Cost Explorer integration for Bedrock cost tracking
- New /admin/costs endpoint with 1-hour caching
- Cost tab showing model costs with usage descriptions
- Daily trend bar chart for last 14 days
- Other AWS costs (collapsed)

Part of #529

## Infrastructure
- Adds ce:GetCostAndUsage IAM permission to Lambda module
- Enabled for API Lambda only

## Test Plan
- [ ] CI passes
- [ ] Terraform plan shows IAM policy addition
- [ ] Cost tab displays in staging after deploy
- [ ] Costs match AWS Cost Explorer console"
```

**Step 4: Watch CI**

Run: `gh pr checks <pr-number> --watch`
Expected: All checks pass

**Step 5: Merge to staging**

Run: `gh pr merge <pr-number> --squash --delete-branch --admin`

---

## Task 8: Apply Terraform and Verify

**Step 1: Apply Terraform changes to staging**

Note: This requires manual approval or CI/CD pipeline.

```bash
cd infra/terraform
AWS_PROFILE=bmx-staging terraform plan -var-file=envs/staging.tfvars
AWS_PROFILE=bmx-staging terraform apply -var-file=envs/staging.tfvars
```

**Step 2: Watch staging deploy**

Run: `gh run list --workflow Deploy --limit 1`
Run: `gh run watch <run-id> --exit-status`

**Step 3: Verify endpoint**

Run: `bmx-api GET /admin/costs`
Expected: JSON response with bedrock_models, daily_trend, etc.

---

## Summary

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Add Cost Explorer IAM to Lambda module | `feat: add Cost Explorer IAM permission` |
| 2 | Enable for API Lambda | `feat: enable Cost Explorer access` |
| 3 | Create cost_explorer service | `feat: add Cost Explorer service` |
| 4 | Add /admin/costs endpoint | `feat: add /admin/costs endpoint` |
| 5 | Add TypeScript types | `feat: add TypeScript types for cost` |
| 6 | Add Cost tab to frontend | `feat: add Cost tab to admin dashboard` |
| 7 | Validation and PR | PR to staging |
| 8 | Terraform apply and verify | Manual step |
