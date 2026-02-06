# BlueMoxon Architecture

## System Overview

BlueMoxon is a serverless book collection management application deployed on AWS with a dual-environment (staging + production) architecture managed by Terraform.

```text
                    ┌─────────────────────────────────────────────┐
                    │          Route 53 (bluemoxon.com)           │
                    └───────────────────┬─────────────────────────┘
                                        │
              ┌─────────────────────────┴─────────────────────────┐
              │                                                    │
    ┌─────────▼─────────┐                          ┌──────────────▼──────────────┐
    │    CloudFront     │                          │         CloudFront          │
    │   (Landing Site)  │                          │         (Vue 3 SPA)         │
    │ bluemoxon.com     │                          │     app.bluemoxon.com       │
    └─────────┬─────────┘                          └──────────────┬──────────────┘
              │                                                    │
    ┌─────────▼─────────┐                          ┌──────────────▼──────────────┐
    │   S3 Bucket       │                          │        S3 Bucket            │
    │ (Landing HTML)    │                          │      (Vue SPA Assets)       │
    └───────────────────┘                          └─────────────────────────────┘

              ┌────────────────────────────────────────────────────┐
              │              API Gateway HTTP API                  │
              │              api.bluemoxon.com                     │
              └───────────────────────┬────────────────────────────┘
                                      │
              ┌───────────────────────▼────────────────────────────┐
              │                  Lambda Function                    │
              │               FastAPI + Mangum                      │
              │                  Python 3.12                        │
              └───────────────────────┬────────────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
┌───────▼───────┐           ┌─────────▼─────────┐          ┌───────▼───────┐
│   Cognito     │           │   Aurora Sv2       │          │   S3 Bucket   │
│  User Pool    │           │   PostgreSQL 16    │          │ (Book Images) │
│ (MFA + Roles) │           │   (Private VPC)    │          │  + Prompts    │
└───────────────┘           └───────────────────┘          └───────────────┘
        │                             │                            │
        │                   ┌─────────▼─────────┐          ┌───────▼───────┐
        │                   │  Secrets Manager   │          │   Bedrock     │
        │                   │  (DB Credentials)  │          │ (Claude 4.5)  │
        │                   └───────────────────┘          │ Napoleon AI   │
        │                                                  └───────────────┘
        │                   ┌───────────────────┐
        │                   │  ElastiCache      │
        │                   │  Redis Serverless │
        │                   │  (Dashboard Cache)│
        │                   └───────────────────┘
```

## Environments

| Environment | Frontend | API | Purpose |
|-------------|----------|-----|---------|
| **Production** | app.bluemoxon.com | api.bluemoxon.com | Live users |
| **Staging** | staging.app.bluemoxon.com | staging.api.bluemoxon.com | Testing before prod |

Both environments are deployed via Terraform with isolated resources (separate Cognito pools, databases, S3 buckets).

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Compute | AWS Lambda + Layers | Cost-effective for low traffic, layers for shared dependencies |
| Database | Aurora Serverless v2 | PostgreSQL for full-text search, scales to zero |
| Auth | Cognito + MFA | Managed auth, built-in 2FA, admin invite only |
| AI Analysis | AWS Bedrock (Opus/Sonnet/Haiku) | Napoleon valuations, entity profiles, order extraction |
| Async Jobs | SQS + Worker Lambda | Decoupled analysis generation, retry handling |
| Frontend | Vue 3 + Vite + Tailwind v4 | User preference, modern tooling, CSS-first configuration |
| Backend | FastAPI | Fast, modern Python, auto-generated docs |
| IaC | **Terraform** | Declarative, well-documented, dual-environment support |

## Terraform Modules

Infrastructure is managed via 15 Terraform modules in `infra/terraform/modules/`:

```mermaid
flowchart TD
    subgraph Modules["Terraform Modules (15)"]
        VPC["vpc-networking<br/>VPC endpoints, NAT Gateway"]
        DNS["dns<br/>Route 53 records"]
        ACM["(ACM certs imported)"]

        S3["s3<br/>Buckets + policies"]
        CF["cloudfront<br/>Distributions + OAC"]
        Landing["landing-site<br/>Static site hosting"]

        Cognito["cognito<br/>User pools + clients"]
        Secrets["secrets<br/>DB credentials"]
        RDS["rds<br/>Aurora Serverless v2"]
        Redis["elasticache<br/>Redis Serverless"]

        Lambda["lambda<br/>API function + IAM"]
        APIGW["api-gateway<br/>HTTP API + routes"]
        DBSync["db-sync-lambda<br/>Prod→Staging sync"]

        OIDC["github-oidc<br/>GitHub Actions auth"]
    end

    VPC --> RDS
    VPC --> Redis
    VPC --> Lambda
    Secrets --> Lambda
    RDS --> Lambda
    Redis --> Lambda
    Cognito --> Lambda
    S3 --> Lambda
    S3 --> CF
    S3 --> Landing
    Lambda --> APIGW
    APIGW --> DNS
    CF --> DNS
    OIDC --> Lambda
```

### Module Responsibilities

| Module | Resources Created |
|--------|-------------------|
| `api-gateway` | HTTP API, custom domain, routes |
| `cloudfront` | Distribution, OAC, cache policies |
| `cognito` | User pool, app client, domain |
| `db-sync-lambda` | Lambda for prod→staging data sync |
| `dns` | Route 53 A/AAAA records |
| `elasticache` | Redis Serverless cache, security group |
| `github-oidc` | OIDC provider, IAM role for GitHub Actions |
| `lambda` | Function, IAM role, VPC config |
| `landing-site` | S3 + CloudFront for marketing site |
| `rds` | Aurora cluster, subnet group, security group |
| `s3` | Buckets for frontend, images, logs |
| `secrets` | Secrets Manager secret + IAM policy |
| `vpc-networking` | VPC endpoints, NAT gateway, route tables |
| `lambda-layers` | Shared Python dependencies layer |
| `sqs` | Analysis and eval runbook job queues |
| `cleanup-lambda` | Database maintenance Lambda |
| `eval-worker-lambda` | Async analysis/eval processing |

## Lambda Architecture

BlueMoxon uses multiple Lambda functions with shared dependency layers:

```mermaid
flowchart TB
    subgraph Layers["Lambda Layers"]
        deps["Dependencies Layer<br/>(boto3, pydantic, sqlalchemy)"]
    end

    subgraph Lambdas["Lambda Functions"]
        api["API Lambda<br/>(FastAPI + Mangum)"]
        worker["Eval Worker Lambda<br/>(SQS Consumer)"]
        cleanup["Cleanup Lambda<br/>(Scheduled)"]
        dbsync["DB Sync Lambda<br/>(Manual Trigger)"]
    end

    subgraph Triggers["Triggers"]
        apigw["API Gateway"]
        sqs["SQS Queues"]
        eventbridge["EventBridge<br/>(Daily Schedule)"]
    end

    deps --> api
    deps --> worker
    deps --> cleanup

    apigw --> api
    sqs --> worker
    eventbridge --> cleanup
```

### Lambda Functions

| Function | Purpose | Trigger | Memory | Timeout |
|----------|---------|---------|--------|---------|
| **API** | FastAPI REST endpoints | API Gateway | 512 MB | 30s |
| **Eval Worker** | Napoleon analysis generation | SQS | 1024 MB | 10 min |
| **Profile Worker** | Entity profile generation (BMX 3.0) | SQS | 1024 MB | 10 min |
| **Cleanup** | Database maintenance, orphan cleanup | EventBridge (daily) | 256 MB | 5 min |
| **DB Sync** | Copy prod data to staging | Manual | 512 MB | 15 min |

### Lambda Layers

Shared dependencies are packaged in a Lambda Layer to reduce deployment size and cold start time:

```text
bluemoxon-deps-layer/
├── python/
│   └── lib/
│       └── python3.12/
│           └── site-packages/
│               ├── boto3/
│               ├── pydantic/
│               ├── sqlalchemy/
│               └── ...
```

**Layer benefits:**

- Reduces API Lambda package from ~80MB to ~5MB
- Shared across all Lambdas (deploy once)
- Faster cold starts (cached by AWS)
- Independent versioning (update deps without code changes)

## SQS Job Processing

Async analysis generation uses SQS for reliability and decoupling:

```mermaid
flowchart LR
    subgraph API["API Lambda"]
        create["POST /analysis/generate-async"]
        status["GET /analysis/status"]
    end

    subgraph Queue["SQS"]
        analysisq["Analysis Queue<br/>(5 min visibility)"]
        dlq["Dead Letter Queue<br/>(3 retries)"]
    end

    subgraph Worker["Eval Worker Lambda"]
        process["Process Job"]
        bedrock["Call Bedrock"]
        save["Save Analysis"]
    end

    subgraph DB["Aurora"]
        jobs["analysis_jobs"]
        analyses["book_analyses"]
    end

    create -->|Send message| analysisq
    create -->|Create job| jobs
    analysisq -->|Trigger| Worker
    process --> bedrock
    bedrock --> save
    save --> analyses
    save -->|Update status| jobs
    status -->|Read| jobs
    analysisq -->|After 3 failures| dlq
```

### SQS Queues

| Queue | Purpose | Visibility | DLQ Retries |
|-------|---------|------------|-------------|
| `analysis-jobs` | Napoleon analysis generation | 5 min | 3 |
| `eval-runbook-jobs` | Evaluation runbook generation | 5 min | 3 |
| `profile-generation` | Entity profile generation (BMX 3.0) | 5 min | 3 |

### Job States

```mermaid
stateDiagram-v2
    [*] --> pending: Job created
    pending --> running: Worker picks up
    running --> completed: Success
    running --> failed: Error
    failed --> pending: Manual retry
    pending --> failed: Stale (>15 min)
```

## Application Architecture

```mermaid
flowchart TB
    subgraph Client["Browser"]
        Vue["Vue 3 SPA<br/>Pinia + Vue Router"]
        Cytoscape["Cytoscape.js<br/>Social Circles Graph"]
    end

    subgraph CDN["AWS CloudFront"]
        CF["CloudFront Distribution"]
    end

    subgraph Frontend["Frontend Hosting"]
        S3F["S3 Bucket<br/>(Static Assets)"]
    end

    subgraph API["API Layer"]
        APIGW["API Gateway<br/>(HTTP API)"]
        Lambda["Lambda Function<br/>(FastAPI + Mangum)"]
    end

    subgraph Async["Async Processing"]
        SQS_Analysis["SQS<br/>(Analysis Queue)"]
        SQS_Profile["SQS<br/>(Profile Queue)"]
        Worker["Eval Worker Lambda"]
        ProfileWorker["Profile Worker Lambda"]
    end

    subgraph Auth["Authentication"]
        Cognito["Cognito User Pool"]
    end

    subgraph Data["Data Layer"]
        Aurora["Aurora PostgreSQL<br/>Serverless v2"]
        S3I["S3 Bucket<br/>(Book Images + Prompts)"]
    end

    subgraph AI["AI Analysis"]
        Bedrock["AWS Bedrock<br/>(Claude Opus/Sonnet/Haiku)"]
    end

    Vue -->|HTTPS| CF
    Cytoscape -->|Graph Data| CF
    CF -->|Static| S3F
    CF -->|/api/*| APIGW
    APIGW --> Lambda
    Lambda --> Aurora
    Lambda --> S3I
    Lambda --> Cognito
    Lambda -->|Napoleon Framework| Bedrock
    Lambda -->|Queue Analysis| SQS_Analysis
    Lambda -->|Queue Profile| SQS_Profile
    SQS_Analysis --> Worker
    SQS_Profile --> ProfileWorker
    Worker --> Bedrock
    ProfileWorker --> Bedrock
    Worker --> Aurora
    ProfileWorker --> Aurora
    Vue -->|Auth| Cognito
```

## Frontend Architecture

The Vue 3 frontend uses Composition API with shared composables for state management and reusable logic.

### Composable Architecture

```mermaid
flowchart TB
    subgraph Views["Views"]
        BooksView["BooksView"]
        BookDetailView["BookDetailView"]
        AdminDashboard["AdminDashboard"]
    end

    subgraph Composables["Composables"]
        useToast["useToast<br/>(notifications)"]
        useDashboardCache["useDashboardCache<br/>(API caching)"]
        useCurrencyConversion["useCurrencyConversion<br/>(GBP/EUR → USD)"]
        useBookImages["useBookImages<br/>(gallery state)"]
    end

    subgraph Services["Services"]
        api["api.ts<br/>(Axios client)"]
        auth["auth.ts<br/>(Cognito)"]
    end

    subgraph State["Pinia Stores"]
        authStore["authStore"]
        toastStore["toastStore"]
    end

    BooksView --> useCurrencyConversion
    BookDetailView --> useBookImages
    AdminDashboard --> useDashboardCache
    Views --> useToast
    useToast --> toastStore
    Views --> api
    api --> authStore
```

### Key Composables

| Composable | Purpose | Features |
|------------|---------|----------|
| `useToast` | Toast notifications | Auto-dismiss, duplicate suppression, hover-to-pause |
| `useDashboardCache` | Dashboard API caching | 5-minute TTL, batch endpoint |
| `useCurrencyConversion` | Currency conversion | Memoized calculations, reactive rates |
| `useBookImages` | Image gallery state | Lightbox, reordering, lazy loading |

### Component Structure

BookDetailView was refactored (#807) into focused sub-components:

```text
BookDetailView/
├── BookDetailView.vue      # Container + routing
├── BookHeader.vue          # Title, status, metadata
├── BookImages.vue          # Gallery + lightbox
├── BookAnalysis.vue        # Napoleon analysis viewer
├── BookScoring.vue         # Investment score breakdown
└── BookActions.vue         # Status changes, edit, delete
```

## Request Flow

```mermaid
sequenceDiagram
    participant B as Browser
    participant CF as CloudFront
    participant S3 as S3 (Static)
    participant API as API Gateway
    participant L as Lambda
    participant DB as Aurora PostgreSQL
    participant IMG as S3 (Images)

    B->>CF: GET /
    CF->>S3: Fetch index.html
    S3-->>CF: HTML + Assets
    CF-->>B: Vue SPA

    B->>CF: GET /api/v1/books
    CF->>API: Forward to API
    API->>L: Invoke Lambda
    L->>DB: Query books
    DB-->>L: Book records
    L-->>API: JSON response
    API-->>CF: 200 OK
    CF-->>B: Book list

    B->>CF: GET /images/book-123.jpg
    CF->>IMG: Fetch image
    IMG-->>CF: Image data
    CF-->>B: Cached image
```

## CI/CD Pipeline

```mermaid
flowchart LR
    subgraph Trigger["Trigger"]
        PR["Pull Request"]
        PushStaging["Push to staging"]
        PushMain["Push to main"]
    end

    subgraph CI["CI Workflow"]
        Lint["Lint + Format"]
        TypeCheck["Type Check"]
        Test["Unit Tests"]
        Security["Security Scan"]
        Build["Build"]
    end

    subgraph DeployStaging["Deploy to Staging"]
        PackageS["Package Lambda"]
        UploadS["Upload to S3"]
        UpdateS["Update Lambda"]
        SmokeS["Smoke Tests"]
    end

    subgraph DeployProd["Deploy to Production"]
        PackageP["Package Lambda"]
        UploadP["Upload to S3"]
        UpdateP["Update Lambda"]
        SmokeP["Smoke Tests"]
    end

    subgraph Infra["Terraform Workflow"]
        Plan["terraform plan"]
        Apply["terraform apply"]
    end

    PR --> CI
    PushStaging --> CI --> DeployStaging
    PushMain --> CI --> DeployProd
    PR --> Plan
    PushStaging --> Apply
```

## Data Model

```mermaid
erDiagram
    BOOKS ||--o{ IMAGES : has
    BOOKS ||--o| ANALYSES : has
    BOOKS ||--o{ ANALYSIS_JOBS : has
    BOOKS }o--|| AUTHORS : written_by
    BOOKS }o--|| PUBLISHERS : published_by
    BOOKS }o--o| BINDERS : bound_by
    AUTHORS ||--o{ ENTITY_PROFILES : has_profile
    PUBLISHERS ||--o{ ENTITY_PROFILES : has_profile
    BINDERS ||--o{ ENTITY_PROFILES : has_profile
    AUTHORS ||--o{ AI_CONNECTIONS : source_or_target
    PUBLISHERS ||--o{ AI_CONNECTIONS : source_or_target
    BINDERS ||--o{ AI_CONNECTIONS : source_or_target

    BOOKS {
        int id PK
        string title
        string publication_date
        int volumes
        string binding_type
        decimal value_low
        decimal value_mid
        decimal value_high
        decimal purchase_price
        string status
        string inventory_type
        string tracking_number
        string tracking_carrier
        string tracking_url
        string tracking_status
        date ship_date
    }

    AUTHORS {
        int id PK
        string name
        int birth_year
        int death_year
        string tier
        boolean preferred
        int priority_score
        string image_url
    }

    PUBLISHERS {
        int id PK
        string name
        string tier
        boolean preferred
        string image_url
    }

    BINDERS {
        int id PK
        string name
        string tier
        boolean preferred
        string full_name
        string image_url
    }

    IMAGES {
        int id PK
        int book_id FK
        string s3_key
        int display_order
        boolean is_primary
        boolean is_garbage
    }

    ANALYSES {
        int id PK
        int book_id FK
        text content
        string model_version
        timestamp updated_at
    }

    ANALYSIS_JOBS {
        int id PK
        int book_id FK
        string status
        string model
        string model_version
        string error_message
        timestamp created_at
        timestamp completed_at
    }

    ENTITY_PROFILES {
        int id PK
        string entity_type
        int entity_id
        text bio_summary
        json personal_stories
        json connection_narratives
        json relationship_stories
        json ai_connections
        string model_version
        timestamp generated_at
    }

    AI_CONNECTIONS {
        int id PK
        string source_type
        int source_id
        string target_type
        int target_id
        string relationship
        string sub_type
        float confidence
        text evidence
    }

    PROFILE_GENERATION_JOBS {
        string id PK
        string status
        int owner_id FK
        int total_entities
        int succeeded
        int failed
        text error_log
        timestamp created_at
        timestamp completed_at
    }

    APP_CONFIG {
        string key PK
        string value
        string description
        timestamp updated_at
        string updated_by
    }
```

### Entity Scoring

Reference entities (Authors, Publishers, Binders) support:

- **Tiers**: TIER_1 (+15 pts), TIER_2 (+10 pts), TIER_3 (+5 pts)
- **Preferred**: +10 pts bonus for preferred entities

### Tracking Status Values

Books with `status=IN_TRANSIT` can have tracking information:

- `pending` - Label created
- `in_transit` - Package in transit
- `out_for_delivery` - Out for delivery
- `delivered` - Delivered
- `exception` - Delivery issue

## Authentication Flow

```mermaid
sequenceDiagram
    participant U as User
    participant App as Vue App
    participant Cog as Cognito
    participant API as API Gateway
    participant Lambda as Lambda

    U->>App: Click Login
    App->>Cog: Redirect to Hosted UI
    U->>Cog: Enter credentials
    Cog-->>App: Authorization code
    App->>Cog: Exchange for tokens
    Cog-->>App: ID + Access tokens
    App->>App: Store tokens (Pinia)

    U->>App: View protected page
    App->>API: GET /api/v1/admin<br/>Authorization: Bearer token
    API->>Lambda: Forward with token
    Lambda->>Cog: Verify token
    Cog-->>Lambda: Token valid
    Lambda-->>API: 200 OK + data
    API-->>App: Protected data
```

## Cost Estimate

| Service | Monthly Cost |
|---------|--------------|
| Aurora Serverless v2 (0.5-2 ACU) | $15-25 |
| Lambda + API Gateway | $1-3 |
| S3 (frontend + images) | $2-3 |
| CloudFront | $2-5 |
| Route 53 + domain | $1-2 |
| Secrets Manager | $1 |
| NAT Gateway | $5-10 |
| **Total** | **$27-49** |

## Security

- **Authentication:** Cognito with required TOTP MFA
- **Authorization:** Role-based (admin/editor/viewer)
- **Encryption:** Aurora and S3 encrypted at rest
- **Network:** Aurora in isolated subnets, Lambda in private subnets with VPC endpoints
- **Transit:** HTTPS enforced via CloudFront
- **API:** JWT validation, Pydantic input validation, rate limiting
- **IaC:** No hardcoded secrets, Secrets Manager integration

## Admin Panel

The Admin Settings page (accessible via profile dropdown for admin users) provides:

### User Management

- **Invite Users:** Send email invitations via Cognito with temporary passwords
- **Role Management:** Assign viewer/editor/admin roles
- **MFA Control:** Enable/disable MFA for users (pool-level MFA required)
- **Password Reset:** Admin can reset any user's password
- **User Impersonation:** Generate temp credentials to test as another user
- **Delete Users:** Remove users from both Cognito and database

### API Key Management

- **Create Keys:** Generate API keys for programmatic access
- **Key Security:** Keys are hashed (SHA-256) before storage; shown only once
- **Revoke Keys:** Deactivate keys without deleting records
- **Audit Trail:** Track last_used_at for each key

### Role-Based Access

| Feature | Viewer | Editor | Admin |
|---------|--------|--------|-------|
| View books/images | Yes | Yes | Yes |
| Edit books/analyses | No | Yes | Yes |
| Upload/reorder images | No | Yes | Yes |
| User management | No | No | Yes |
| API key management | No | No | Yes |

## Viewing Diagrams

These Mermaid diagrams render in:

- **GitHub**: Automatically in markdown preview
- **VS Code**: With Mermaid extension
- **Mermaid Live Editor**: <https://mermaid.live>

---

*Last Updated: February 2026*
