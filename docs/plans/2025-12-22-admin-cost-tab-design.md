# Admin Cost Tab Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a Cost tab to the Admin Config Dashboard showing Bedrock usage costs by model with usage descriptions.

**Architecture:** New `/admin/costs` endpoint fetches AWS Cost Explorer data, caches for 1 hour, returns structured cost breakdown. Frontend displays in new tab with table and simple bar chart.

**Tech Stack:** AWS Cost Explorer API (boto3), FastAPI, Vue 3, TypeScript

---

## Backend

### New Endpoint: `GET /admin/costs`

**Response Model:**
```python
class BedrockModelCost(BaseModel):
    model_name: str        # "Sonnet 4.5", "Opus 4.5", "Haiku 3"
    usage: str             # "Napoleon analysis, Eval runbooks..."
    mtd_cost: float        # Month-to-date cost in USD

class DailyCost(BaseModel):
    date: str              # "2025-12-21"
    cost: float            # Total Bedrock cost that day

class CostResponse(BaseModel):
    period_start: str      # "2025-12-01"
    period_end: str        # "2025-12-22"
    bedrock_models: list[BedrockModelCost]
    bedrock_total: float
    daily_trend: list[DailyCost]  # Last 14 days
    other_costs: dict[str, float]  # {"Lambda": 0.01, "RDS": 7.44, ...}
    total_aws_cost: float
    cached_at: str         # When data was fetched
```

### AWS Service Name Mapping

Map Cost Explorer service names to our model names + usage:

| AWS Service Name | Model Name | Usage |
|------------------|------------|-------|
| Claude Sonnet 4.5 (Amazon Bedrock Edition) | Sonnet 4.5 | Napoleon analysis, Eval runbooks, FMV lookup, Listing extraction |
| Claude Opus 4.5 (Amazon Bedrock Edition) | Opus 4.5 | Napoleon analysis (high quality) |
| Claude 3 Haiku (Amazon Bedrock Edition) | Haiku 3 | Order data extraction |
| Claude 3.5 Sonnet* | Sonnet 3.5 (legacy) | Legacy usage |

### Caching

- Cache response in memory for 1 hour
- Simple dict: `{data: CostResponse, fetched_at: datetime}`
- Cost Explorer updates hourly, no benefit to more frequent calls

### Other AWS Costs to Include

- AWS Lambda
- Amazon RDS
- Amazon VPC
- Amazon S3
- Amazon CloudFront
- Amazon API Gateway

---

## Frontend

### New Tab: "Cost"

Fourth tab after "Tiered Entities".

### Components

**1. Bedrock Usage Costs Table**
- Model name, usage description, MTD cost
- Total row at bottom
- Period shown in header (e.g., "December 2025")

**2. Daily Trend**
- Last 14 days of Bedrock spend
- Simple horizontal bar chart using CSS (no library)
- Date, bar, cost value

**3. Other AWS Costs (collapsed)**
- Expandable section showing non-Bedrock costs
- Simple key-value list
- Total AWS cost

**4. Cache indicator**
- "Last updated: {time} UTC (cached 1hr)"

### TypeScript Types

```typescript
interface BedrockModelCost {
  model_name: string;
  usage: string;
  mtd_cost: number;
}

interface DailyCost {
  date: string;
  cost: number;
}

interface CostResponse {
  period_start: string;
  period_end: string;
  bedrock_models: BedrockModelCost[];
  bedrock_total: number;
  daily_trend: DailyCost[];
  other_costs: Record<string, number>;
  total_aws_cost: number;
  cached_at: string;
}
```

---

## Infrastructure

### IAM Permission

Add to Lambda execution role (Terraform):

```hcl
statement {
  effect    = "Allow"
  actions   = ["ce:GetCostAndUsage"]
  resources = ["*"]
}
```

Cost Explorer doesn't support resource-level permissions.

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Cost Explorer API fails | Show "Cost data unavailable" message |
| No data for period | Show $0.00 with note |
| API error | Cache error state for 5 minutes |

---

## Security

- Endpoint requires admin auth (same as `/admin/system-info`)
- Uses Lambda execution role for AWS credentials
- Production costs only (staging has minimal spend)

---

## Files to Modify

### Backend
- `backend/app/api/v1/admin.py` - Add `/costs` endpoint and models
- `backend/app/services/cost_explorer.py` - New service for AWS Cost Explorer

### Frontend
- `frontend/src/types/admin.ts` - Add cost types
- `frontend/src/views/AdminConfigView.vue` - Add Cost tab

### Infrastructure
- `infra/terraform/modules/lambda/main.tf` - Add ce:GetCostAndUsage permission
