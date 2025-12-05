# BlueMoxon Architecture Diagrams

## 1. Application Architecture

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

## 2. Request Flow

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

## 3. CI/CD Pipeline

```mermaid
flowchart LR
    subgraph Trigger["Trigger"]
        Push["Push to main"]
        PR["Pull Request"]
    end

    subgraph CI["CI Workflow (ci.yml)"]
        Lint["Lint<br/>ruff check"]
        TypeCheck["Type Check<br/>mypy"]
        Test["Unit Tests<br/>pytest"]
        Security["Security Scan<br/>pip-audit"]
        Build["Build Frontend<br/>npm run build"]
    end

    subgraph Deploy["Deploy Workflow (deploy.yml)"]
        Package["Package Lambda<br/>zip backend"]
        CDK["CDK Deploy<br/>8 stacks"]
        Upload["Upload Frontend<br/>S3 sync"]
        Invalidate["Invalidate Cache<br/>CloudFront"]
        Smoke["Smoke Test<br/>Health check"]
    end

    subgraph AWS["AWS"]
        Prod["Production<br/>Environment"]
    end

    Push --> CI
    PR --> CI
    Lint --> TypeCheck
    TypeCheck --> Test
    Test --> Security
    Security --> Build
    Build -->|main only| Deploy
    Package --> CDK
    CDK --> Upload
    Upload --> Invalidate
    Invalidate --> Smoke
    Smoke --> Prod
```

## 4. CI Checks Detail

```mermaid
flowchart TD
    subgraph Linting["Code Quality"]
        Ruff["ruff check<br/>Python linting"]
        RuffFmt["ruff format --check<br/>Code formatting"]
    end

    subgraph Types["Type Safety"]
        Mypy["mypy<br/>Static type checking"]
    end

    subgraph Testing["Testing"]
        Pytest["pytest<br/>Unit tests"]
        Cov["Coverage Report"]
    end

    subgraph Security["Security"]
        Audit["pip-audit<br/>Dependency vulnerabilities"]
    end

    subgraph Frontend["Frontend Build"]
        NPM["npm ci<br/>Install deps"]
        TSC["TypeScript check"]
        Vite["vite build<br/>Production bundle"]
    end

    Ruff --> RuffFmt
    RuffFmt --> Mypy
    Mypy --> Pytest
    Pytest --> Cov
    Cov --> Audit
    Audit --> NPM
    NPM --> TSC
    TSC --> Vite
```

## 5. AWS Infrastructure

```mermaid
flowchart TB
    subgraph Internet["Internet"]
        User["Users"]
    end

    subgraph Route53["DNS"]
        DNS["Route 53<br/>bluemoxon.com"]
    end

    subgraph Edge["Edge"]
        CF["CloudFront<br/>Distribution"]
        ACM["ACM Certificate<br/>*.bluemoxon.com"]
    end

    subgraph Storage["Storage"]
        S3F["S3: Frontend<br/>www.bluemoxon.com"]
        S3I["S3: Images<br/>images.bluemoxon.com"]
    end

    subgraph Compute["Compute"]
        APIGW["API Gateway<br/>HTTP API"]
        Lambda["Lambda<br/>Python 3.12<br/>FastAPI"]
    end

    subgraph Auth["Authentication"]
        Cognito["Cognito<br/>User Pool"]
    end

    subgraph Database["Database"]
        subgraph VPC["VPC"]
            subgraph Private["Private Subnets"]
                Aurora["Aurora PostgreSQL<br/>Serverless v2"]
            end
        end
    end

    subgraph Secrets["Secrets"]
        SM["Secrets Manager<br/>DB Credentials"]
    end

    User --> DNS
    DNS --> CF
    CF --> ACM
    CF --> S3F
    CF --> S3I
    CF --> APIGW
    APIGW --> Lambda
    Lambda --> Aurora
    Lambda --> S3I
    Lambda --> Cognito
    Lambda --> SM
```

## 6. CDK Stack Dependencies

```mermaid
flowchart TD
    subgraph Stacks["8 CDK Stacks"]
        Network["NetworkStack<br/>VPC, Subnets"]
        Database["DatabaseStack<br/>Aurora, Secrets"]
        Auth["AuthStack<br/>Cognito"]
        Storage["StorageStack<br/>S3 Buckets"]
        API["ApiStack<br/>Lambda, API Gateway"]
        Frontend["FrontendStack<br/>S3 + OAC"]
        DNS["DnsStack<br/>Route 53, CloudFront"]
        Pipeline["PipelineStack<br/>GitHub OIDC"]
    end

    Network --> Database
    Network --> API
    Database --> API
    Auth --> API
    Storage --> API
    Storage --> DNS
    API --> DNS
    Frontend --> DNS
```

## 7. Data Model

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

## 8. Authentication Flow

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

---

## Viewing These Diagrams

These Mermaid diagrams can be rendered in:
- **GitHub**: Automatically renders in markdown preview
- **VS Code**: With Mermaid extension
- **Mermaid Live Editor**: https://mermaid.live
- **Obsidian**: Native Mermaid support
- **Notion**: Paste code blocks with mermaid language

To export as images, use:
```bash
# Install mermaid-cli
npm install -g @mermaid-js/mermaid-cli

# Convert to PNG
mmdc -i ARCHITECTURE_DIAGRAMS.md -o diagrams/
```
