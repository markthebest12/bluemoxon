# Admin Dashboard User Guide

The Admin Dashboard provides system monitoring, configuration management, and cost tracking for BlueMoxon administrators and editors.

**Access:** Navigate to **Config** in the main menu (requires Editor or Admin role).

---

## Tabs Overview

| Tab | Purpose | Updates |
|-----|---------|---------|
| **Settings** | Currency exchange rates | Manual save |
| **System Status** | Health checks, version info | On page load |
| **Models** | AI model configuration per workflow | Editable (Admin) |
| **Scoring Config** | Recommendation algorithm settings | Read-only |
| **Entity Tiers** | Author/Publisher/Binder tiers | Read-only |
| **Reference Data** | CRUD for Authors/Publishers/Binders | Real-time |
| **Maintenance** | Database cleanup, orphan detection | Manual trigger |
| **Cost** | AWS Bedrock usage costs | Cached 1 hour |

---

## Settings Tab

Manage currency conversion rates for acquisition costs entered in foreign currencies.

| Field | Description | Default |
|-------|-------------|---------|
| GBP to USD | British Pound conversion rate | 1.28 |
| EUR to USD | Euro conversion rate | 1.10 |

**Usage:** When entering acquisition costs in GBP or EUR, the system converts to USD using these rates.

---

## System Status Tab

Real-time system health and deployment information.

### Version Info

- **Version** - Current deployed version (format: `YYYY.MM.DD-<sha>`)
- **Git SHA** - Full commit hash for traceability
- **Deploy Time** - When this version was deployed (your local timezone)
- **Environment** - `staging` or `production`

### Health Checks

| Service | What It Checks |
|---------|----------------|
| **Database** | PostgreSQL connection, returns book count |
| **S3** | Images bucket accessibility |
| **Cognito** | User pool connectivity |

**Status indicators:**

- 🟢 `healthy` - Service responding normally
- 🟡 `skipped` - Service not configured (e.g., Cognito in local dev)
- 🔴 `unhealthy` - Service unreachable or erroring

### Cold Start Indicator

Shows if this request triggered a Lambda cold start (first request after idle period).

---

## Models Tab

Configurable AI model assignments per workflow (BMX 3.0). Admin users can change which model is used for each workflow. Editors see a read-only display.

### Available Models

| Model | Model ID | Typical Usage |
|-------|----------|---------------|
| **Sonnet 4.5** | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | Eval runbooks, FMV lookup, listing extraction |
| **Opus 4.6** | `us.anthropic.claude-opus-4-6-v1` | Napoleon analysis (default) |
| **Haiku 3.5** | `anthropic.claude-3-5-haiku-20241022-v1:0` | Entity profiles, order extraction |

### Configurable Workflows

| Flow | Default Model | Description |
|------|---------------|-------------|
| **Napoleon Analysis** | Opus | Full book analysis using the Napoleon framework |
| **Entity Profiles** | Haiku | AI-generated biographical profiles for authors, publishers, and binders |
| **Order Extraction** | Haiku | Structured data extraction from order emails |

Each workflow shows a dropdown selector (admin only) to change the model. Changes are stored in the `app_config` table with 5-minute cache TTL. A "Reset to Default" button reverts to the hardcoded default.

---

## Scoring Config Tab

Displays the algorithm constants used for book recommendation scoring. Key tunables are marked with ★.

### Quality Points

Points awarded for collection quality factors:

- Publisher/Binder tier bonuses
- Condition bonuses (Fine, Good)
- Era bonuses (Victorian, Romantic)
- Complete set bonus
- Penalties for duplicates and large volumes

### Strategic Points

Points for collection-building strategy:

- New author acquisition
- Second work by existing author
- Completing a set
- Publisher focus match

### Thresholds

Score boundaries that determine recommendations:

- **Price thresholds** - Excellent (<60%), Good (<75%), Fair (<85%)
- **Floor scores** - Minimum scores to qualify for recommendation

### Offer Discounts

Suggested discount percentages based on investment grade:

- Grade 70-79: 15% discount
- Grade 60-69: 20% discount
- Grade 50-59: 25% discount
- etc.

---

## Entity Tiers Tab

Displays tiered authors, publishers, and binders that receive scoring bonuses.

### Tier Hierarchy

| Tier | Bonus | Description |
|------|-------|-------------|
| **Tier 1** | +15 pts | Premium/most desirable |
| **Tier 2** | +10 pts | Notable/collectible |
| **Tier 3** | +5 pts | Of interest |

### Current Tiers

Lists all entities with assigned tiers, grouped by type:

- **Authors** - e.g., Darwin, Dickens, Lyell
- **Publishers** - e.g., John Murray, Chapman & Hall
- **Binders** - e.g., Zaehnsdorf, Rivière & Son

---

## Reference Data Tab

Full CRUD interface for managing reference entities (Authors, Publishers, Binders).

### Entity Lists

Three sub-tabs for each entity type:

- **Authors** - Manage author records
- **Publishers** - Manage publisher records
- **Binders** - Manage binder/bindery records

### Entity Actions

| Action | Description | Requirements |
|--------|-------------|--------------|
| **Create** | Add new entity | Editor role |
| **Edit** | Modify entity fields | Editor role |
| **Delete** | Remove entity (if no books) | Editor role |
| **Reassign** | Move books to another entity, then delete | Editor role |

### Entity Fields

**Authors:**

- Name (required)
- Birth/Death years
- Era (Victorian, Romantic, etc.)
- Tier (Tier 1/2/3)
- Preferred (bonus scoring)
- Priority Score

**Publishers:**

- Name (required)
- Founded year
- Description
- Tier (Tier 1/2/3)
- Preferred (bonus scoring)

**Binders:**

- Name (required)
- Full Name (e.g., "Rivière & Son")
- Authentication Markers
- Tier (Tier 1/2/3)
- Preferred (bonus scoring)

### Reassignment

Use reassignment when merging duplicate entities:

1. Click the **Reassign** button (↔️) on the source entity
2. Select the target entity from the dropdown
3. Confirm the operation
4. All books are moved to target, source is deleted

**Example:** Merge "W.M. Thackeray" into "William Makepeace Thackeray"

---

## Maintenance Tab

Database maintenance and cleanup operations.

### Orphan Detection

Identifies database records without proper relationships:

- Images without books
- Analyses without books
- Jobs without books

### Cleanup Operations

| Operation | Description | Safety |
|-----------|-------------|--------|
| **Cleanup Orphans** | Remove orphaned records | Safe - only removes broken refs |
| **Vacuum Database** | Reclaim disk space | Safe - PostgreSQL maintenance |
| **Refresh Stats** | Update query planner stats | Safe - improves performance |

### Garbage Image Review

Review images flagged as "garbage" by AI:

- View flagged images
- Override classification if incorrect
- Permanently delete confirmed garbage

---

## Cost Tab

AWS Bedrock usage costs for the current month.

### Bedrock Model Costs

Table showing month-to-date costs per AI model:

- Model name and usage description
- MTD cost in USD

### Daily Trend

Bar chart showing Bedrock costs over the last 14 days. Useful for:

- Identifying usage spikes
- Monitoring cost trends
- Correlating with activity

### Other AWS Costs

Collapsible section showing non-Bedrock AWS costs:

- S3 storage
- CloudFront CDN
- RDS database
- Other services

### Caching

Cost data is **cached for 1 hour** to minimize AWS Cost Explorer API calls. The `cached_at` timestamp shows when data was last fetched.

---

## Troubleshooting

### Dashboard won't load

1. Check browser console for errors
2. Verify you have Editor or Admin role
3. Try refreshing the page

### Health check shows unhealthy

1. Check the specific service error message
2. For database: verify RDS is running
3. For S3: check bucket permissions
4. For Cognito: verify user pool exists

### Cost tab shows error

- Cost Explorer permission may not be configured
- Only works in deployed environments (not local dev)
- Data may be unavailable for new AWS accounts

### Stale cost data

Cost data caches for 1 hour. Wait for cache expiry or check `cached_at` timestamp.

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/admin/system-info` | GET | System status, health, config |
| `/admin/costs` | GET | AWS cost data |
| `/admin/config` | GET | Currency rates |
| `/admin/config` | PUT | Update currency rates (Admin only) |
| `/admin/model-config` | GET | Model assignments per workflow (Admin only) |
| `/admin/model-config/{flow_key}` | PUT | Update model for a workflow (Admin only) |

See [API Reference](API_REFERENCE.md#admin-dashboard-api-editor) for full documentation.
