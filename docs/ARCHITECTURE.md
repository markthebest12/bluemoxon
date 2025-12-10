# BlueMoxon Architecture

## System Overview

BlueMoxon is a serverless book collection management application deployed on AWS with a dual-environment (staging + production) architecture managed by Terraform.

```
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
│ (MFA + Roles) │           │   (Private VPC)    │          │               │
└───────────────┘           └───────────────────┘          └───────────────┘
                                      │
                            ┌─────────▼─────────┐
                            │  Secrets Manager   │
                            │  (DB Credentials)  │
                            └───────────────────┘
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
| Compute | AWS Lambda | Cost-effective for low traffic, cold starts acceptable |
| Database | Aurora Serverless v2 | PostgreSQL for full-text search, scales to zero |
| Auth | Cognito + MFA | Managed auth, built-in 2FA, admin invite only |
| Frontend | Vue 3 + Vite | User preference, modern tooling |
| Backend | FastAPI | Fast, modern Python, auto-generated docs |
| IaC | **Terraform** | Declarative, well-documented, dual-environment support |

## Terraform Modules

Infrastructure is managed via 14 Terraform modules in `infra/terraform/modules/`:

```mermaid
flowchart TD
    subgraph Modules["Terraform Modules (14)"]
        VPC["vpc-networking<br/>VPC endpoints, NAT Gateway"]
        DNS["dns<br/>Route 53 records"]
        ACM["(ACM certs imported)"]

        S3["s3<br/>Buckets + policies"]
        CF["cloudfront<br/>Distributions + OAC"]
        Landing["landing-site<br/>Static site hosting"]

        Cognito["cognito<br/>User pools + clients"]
        Secrets["secrets<br/>DB credentials"]
        RDS["rds<br/>Aurora Serverless v2"]

        Lambda["lambda<br/>API function + IAM"]
        APIGW["api-gateway<br/>HTTP API + routes"]
        DBSync["db-sync-lambda<br/>Prod→Staging sync"]

        OIDC["github-oidc<br/>GitHub Actions auth"]
    end

    VPC --> RDS
    VPC --> Lambda
    Secrets --> Lambda
    RDS --> Lambda
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
| `github-oidc` | OIDC provider, IAM role for GitHub Actions |
| `lambda` | Function, IAM role, VPC config |
| `landing-site` | S3 + CloudFront for marketing site |
| `rds` | Aurora cluster, subnet group, security group |
| `s3` | Buckets for frontend, images, logs |
| `secrets` | Secrets Manager secret + IAM policy |
| `vpc-networking` | VPC endpoints, NAT gateway, route tables |

## Application Architecture

```mermaid
flowchart TB
    subgraph Client["Browser"]
        Vue["Vue 3 SPA<br/>Pinia + Vue Router"]
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

    subgraph Auth["Authentication"]
        Cognito["Cognito User Pool"]
    end

    subgraph Data["Data Layer"]
        Aurora["Aurora PostgreSQL<br/>Serverless v2"]
        S3I["S3 Bucket<br/>(Book Images)"]
    end

    Vue -->|HTTPS| CF
    CF -->|Static| S3F
    CF -->|/api/*| APIGW
    APIGW --> Lambda
    Lambda --> Aurora
    Lambda --> S3I
    Lambda --> Cognito
    Vue -->|Auth| Cognito
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
    BOOKS }o--|| AUTHORS : written_by
    BOOKS }o--|| PUBLISHERS : published_by
    BOOKS }o--o| BINDERS : bound_by

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
    }

    AUTHORS {
        int id PK
        string name
        string birth_year
        string death_year
    }

    PUBLISHERS {
        int id PK
        string name
        string tier
    }

    BINDERS {
        int id PK
        string name
        boolean is_premium
    }

    IMAGES {
        int id PK
        int book_id FK
        string s3_key
        int display_order
        boolean is_primary
    }

    ANALYSES {
        int id PK
        int book_id FK
        text content
        timestamp updated_at
    }
```

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
- **Mermaid Live Editor**: https://mermaid.live

---

*Last Updated: December 2025*
