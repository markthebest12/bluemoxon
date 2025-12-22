# Admin Dashboard User Guide

The Admin Dashboard provides system monitoring, configuration management, and cost tracking for BlueMoxon administrators and editors.

**Access:** Navigate to **Config** in the main menu (requires Editor or Admin role).

---

## Tabs Overview

| Tab | Purpose | Updates |
|-----|---------|---------|
| **Settings** | Currency exchange rates | Manual save |
| **System Status** | Health checks, version info | On page load |
| **Models** | AI model configuration | Read-only |
| **Scoring Config** | Recommendation algorithm settings | Read-only |
| **Entity Tiers** | Author/Publisher/Binder tiers | Read-only |
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

Read-only display of configured AI models and their purposes.

| Model | Typical Usage |
|-------|---------------|
| **Sonnet 4.5** | Primary book analysis |
| **Opus 4.5** | Complex reasoning tasks |
| **Haiku** | Fast extraction tasks |

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

See [API Reference](API_REFERENCE.md#admin-dashboard-api-editor) for full documentation.
