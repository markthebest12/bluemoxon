# BlueMoxon AWS Infrastructure

## Overview

BlueMoxon is deployed on AWS using a serverless architecture optimized for low-traffic applications with cost efficiency. The infrastructure was provisioned using AWS CLI on November 30, 2025.

**Region:** us-west-2 (Oregon)
**Account:** 266672885920
**Domain:** bluemoxon.com

## Architecture Diagram

```mermaid
graph TB
    subgraph Internet
        User[User Browser]
    end

    subgraph AWS["AWS Cloud (us-west-2)"]
        subgraph Edge["Edge Services"]
            R53[Route 53<br/>bluemoxon.com]
            CF[CloudFront<br/>E16BJX90QWQNQO]
            ACM[ACM Certificate<br/>*.bluemoxon.com]
        end

        subgraph Storage["Storage Layer"]
            S3F[S3: bluemoxon-frontend<br/>Vue SPA Assets]
            S3I[S3: bluemoxon-images<br/>Book Images]
        end

        subgraph Auth["Authentication"]
            COG[Cognito User Pool<br/>us-west-2_PvdIpXVKF<br/>MFA Required]
        end

        subgraph Compute["Compute Layer"]
            APIGW[API Gateway HTTP<br/>h7q9ga51xa]
            Lambda[Lambda: bluemoxon-api<br/>Python 3.11 / FastAPI]
        end

        subgraph VPC["VPC: vpc-023f4b1dc7c2c4296 (10.0.0.0/16)"]
            subgraph Public["Public Subnets (10.0.1-2.0/24)"]
                IGW[Internet Gateway]
                NAT[NAT Gateway]
            end

            subgraph Private["Private Subnets (10.0.11-12.0/24)"]
                LambdaENI[Lambda ENI]
            end

            subgraph Isolated["Isolated Subnets (10.0.21-22.0/24)"]
                Aurora[(Aurora Serverless v2<br/>PostgreSQL 16.10<br/>0.5-2 ACU)]
            end
        end

        subgraph Secrets["Secrets Management"]
            SM[Secrets Manager<br/>bluemoxon/db-credentials]
        end
    end

    User -->|HTTPS| R53
    R53 -->|A/AAAA Alias| CF
    CF -->|OAC| S3F
    CF -.->|TLS| ACM

    User -->|API Calls| APIGW
    APIGW --> Lambda
    Lambda --> LambdaENI
    LambdaENI -->|Port 5432| Aurora
    Lambda -->|GetSecretValue| SM
    Lambda -->|Read/Write| S3I
    Lambda -.->|Validate JWT| COG

    IGW --> NAT
    NAT --> LambdaENI
```

## Application Flow Diagrams

### Authentication Flow

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend<br/>(Vue SPA)
    participant COG as Cognito
    participant API as API Gateway
    participant L as Lambda

    Note over U,L: Initial Login (Admin Invite Only)

    U->>FE: Navigate to /login
    FE->>COG: Redirect to Hosted UI
    U->>COG: Enter email + temp password
    COG->>U: Prompt: Set new password
    U->>COG: Set permanent password
    COG->>U: Prompt: Setup MFA (TOTP)
    U->>COG: Scan QR code, enter TOTP
    COG->>FE: Return authorization code
    FE->>COG: Exchange code for tokens
    COG->>FE: Return ID + Access + Refresh tokens
    FE->>FE: Store tokens in memory

    Note over U,L: Authenticated API Request

    U->>FE: View books
    FE->>API: GET /api/v1/books<br/>Authorization: Bearer {access_token}
    API->>L: Invoke with JWT
    L->>L: Validate JWT with Cognito JWKS
    L->>L: Query Aurora
    L->>API: Return books JSON
    API->>FE: 200 OK + books data
    FE->>U: Render book list

    Note over U,L: Token Refresh

    FE->>FE: Access token expired
    FE->>COG: POST /oauth2/token<br/>grant_type=refresh_token
    COG->>FE: New access + ID tokens
```

### Book Management Flows

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant API as API Gateway
    participant L as Lambda
    participant DB as Aurora PostgreSQL
    participant S3 as S3 Images

    Note over U,S3: Search Books

    U->>FE: Enter search query
    FE->>API: GET /api/v1/books/search?q=dickens
    API->>L: Invoke
    L->>DB: SELECT with full-text search
    DB->>L: Return matching books
    L->>API: JSON response
    API->>FE: Books with thumbnails
    FE->>U: Display results grid

    Note over U,S3: View Book Details

    U->>FE: Click on book card
    FE->>API: GET /api/v1/books/{id}
    API->>L: Invoke
    L->>DB: SELECT book + images + analysis
    DB->>L: Book data
    L->>API: Full book JSON
    API->>FE: Book details
    FE->>S3: Load images via CloudFront
    S3->>FE: Image data
    FE->>U: Render detail view

    Note over U,S3: Create New Book

    U->>FE: Fill book form
    U->>FE: Upload images
    FE->>API: POST /api/v1/books
    API->>L: Invoke with book data
    L->>DB: INSERT book record
    DB->>L: Return book ID
    L->>API: 201 Created

    loop For each image
        FE->>API: POST /api/v1/books/{id}/images
        API->>L: Invoke with image
        L->>S3: PUT image object
        S3->>L: Success
        L->>DB: INSERT image record
        L->>API: Image URL
    end

    API->>FE: Complete
    FE->>U: Show success, redirect to detail

    Note over U,S3: Edit Book

    U->>FE: Modify book fields
    FE->>API: PUT /api/v1/books/{id}
    API->>L: Invoke with updates
    L->>DB: UPDATE book record
    DB->>L: Success
    L->>API: 200 OK
    API->>FE: Updated book
    FE->>U: Show saved confirmation

    Note over U,S3: Delete Book

    U->>FE: Click delete, confirm
    FE->>API: DELETE /api/v1/books/{id}
    API->>L: Invoke
    L->>DB: Get associated images
    DB->>L: Image list
    loop For each image
        L->>S3: DELETE image object
    end
    L->>DB: DELETE book (cascade)
    DB->>L: Success
    L->>API: 204 No Content
    API->>FE: Success
    FE->>U: Redirect to book list
```

## Resource Inventory

### Networking

| Resource | ID/ARN | Details |
|----------|--------|---------|
| VPC | `vpc-023f4b1dc7c2c4296` | CIDR: 10.0.0.0/16, DNS enabled |
| Internet Gateway | `igw-0c8c2413e3958ec04` | Attached to VPC |
| NAT Gateway | `nat-0551444ab65c31f8c` | In public-a subnet |
| Elastic IP | `eipalloc-098bcae03133fb25a` | For NAT Gateway |

**Subnets:**

| Name | ID | CIDR | AZ | Purpose |
|------|-----|------|-----|---------|
| public-a | `subnet-0b170eacdfed1ec3a` | 10.0.1.0/24 | us-west-2a | NAT Gateway |
| public-b | `subnet-04e95aa299c6e1018` | 10.0.2.0/24 | us-west-2b | Redundancy |
| private-a | `subnet-026cb4a2cf0464f88` | 10.0.11.0/24 | us-west-2a | Lambda |
| private-b | `subnet-0ffc724f850e0a438` | 10.0.12.0/24 | us-west-2b | Lambda |
| isolated-a | `subnet-037b7953df0ccd042` | 10.0.21.0/24 | us-west-2a | Aurora |
| isolated-b | `subnet-03e9217cb4472f0a0` | 10.0.22.0/24 | us-west-2b | Aurora |

**Route Tables:**

| Name | ID | Routes |
|------|-----|--------|
| public | `rtb-047fb09852afa8c21` | 0.0.0.0/0 → IGW |
| private | `rtb-03b11ae30d0b64149` | 0.0.0.0/0 → NAT |
| isolated | `rtb-082c18ad4fd08b193` | Local only |

**Security Groups:**

| Name | ID | Inbound | Outbound |
|------|-----|---------|----------|
| aurora-sg | `sg-0bdf28db1cea9797e` | 5432 from lambda-sg | None |
| lambda-sg | `sg-0ae3f0f22c08e0c62` | None | All traffic |

### Database

| Resource | Value |
|----------|-------|
| Cluster ID | `bluemoxon-cluster` |
| Instance ID | `bluemoxon-instance-1` |
| Engine | Aurora PostgreSQL 16.10 |
| Instance Class | db.serverless (0.5-2 ACU) |
| Endpoint | `bluemoxon-cluster.cluster-cp4c0cuuyq2m.us-west-2.rds.amazonaws.com` |
| Reader Endpoint | `bluemoxon-cluster.cluster-ro-cp4c0cuuyq2m.us-west-2.rds.amazonaws.com` |
| Port | 5432 |
| Database Name | `bluemoxon` |
| Subnet Group | `bluemoxon-db-subnet-group` |
| Encryption | Enabled (AWS managed key) |
| Backup Retention | 7 days |

### Authentication

| Resource | Value |
|----------|-------|
| User Pool ID | `us-west-2_PvdIpXVKF` |
| App Client ID | `3ndaok3psd2ncqfjrdb57825he` |
| Domain | `bluemoxon.auth.us-west-2.amazoncognito.com` |
| MFA | Required (TOTP) |
| Self-Signup | Disabled (admin invite only) |
| Password Policy | 12+ chars, upper, lower, number, symbol |

### Compute

| Resource | Value |
|----------|-------|
| Function Name | `bluemoxon-api` |
| Function ARN | `arn:aws:lambda:us-west-2:266672885920:function:bluemoxon-api` |
| Runtime | Python 3.11 |
| Handler | `app.main.handler` |
| Memory | 512 MB |
| Timeout | 30 seconds |
| Role | `bluemoxon-lambda-role` |

**Environment Variables:**

| Variable | Value |
|----------|-------|
| DATABASE_URL | `postgresql://bluemoxon_admin@{endpoint}:5432/bluemoxon` |
| SECRET_ARN | `arn:aws:secretsmanager:us-west-2:266672885920:secret:bluemoxon/db-credentials-Firmtl` |
| CORS_ORIGINS | `https://bluemoxon.com` |
| S3_IMAGES_BUCKET | `bluemoxon-images` |
| DEBUG | `false` |

### API Gateway

| Resource | Value |
|----------|-------|
| API ID | `h7q9ga51xa` |
| Type | HTTP API |
| Endpoint | `https://h7q9ga51xa.execute-api.us-west-2.amazonaws.com` |
| Stage | `$default` (auto-deploy) |
| CORS | Enabled for bluemoxon.com, localhost:5173 |

### Storage

| Bucket | Purpose | Features |
|--------|---------|----------|
| `bluemoxon-frontend` | Vue SPA static files | Versioning, CloudFront OAC |
| `bluemoxon-images` | Book images | Versioning, CORS enabled |

### CDN & DNS

| Resource | Value |
|----------|-------|
| CloudFront Distribution | `E16BJX90QWQNQO` |
| CloudFront Domain | `d2yd5bvqaomg54.cloudfront.net` |
| Origin Access Control | `EZGSJYMZAFG0S` |
| ACM Certificate | `arn:aws:acm:us-east-1:266672885920:certificate/92395aeb-a01e-4a48-b4bd-0a9f1c04e861` |
| Hosted Zone ID | `Z09346283AE9VMIQQJ8VL` |

### Secrets

| Secret | ARN |
|--------|-----|
| DB Credentials | `arn:aws:secretsmanager:us-west-2:266672885920:secret:bluemoxon/db-credentials-Firmtl` |

## Cost Estimate

| Service | Monthly Cost |
|---------|--------------|
| Aurora Serverless v2 (0.5-2 ACU) | $15-25 |
| NAT Gateway | $5-10 |
| Lambda + API Gateway | $1-3 |
| S3 (frontend + images) | $2-3 |
| CloudFront | $2-5 |
| Route 53 + domain | $1-2 |
| Secrets Manager | $1 |
| **Total** | **$27-49** |

## Deployment Commands

### Update Lambda Code

```bash
# Build deployment package (requires Docker)
docker run --rm \
  -v $(pwd)/backend:/app:ro \
  -v /tmp/lambda-deploy:/output \
  --platform linux/amd64 \
  amazonlinux:2023 \
  /bin/bash -c "
    dnf install -y python3.11 python3.11-pip zip > /dev/null 2>&1
    python3.11 -m pip install -q -t /output -r /app/requirements.txt
    cp -r /app/app /output/
  "

cd /tmp/lambda-deploy
zip -q -r /tmp/bluemoxon-api.zip . -x "*.pyc" -x "*__pycache__*"

# Upload and update Lambda
aws s3 cp /tmp/bluemoxon-api.zip s3://bluemoxon-frontend/lambda/bluemoxon-api.zip --profile bluemoxon
aws lambda update-function-code \
  --function-name bluemoxon-api \
  --s3-bucket bluemoxon-frontend \
  --s3-key lambda/bluemoxon-api.zip \
  --profile bluemoxon --region us-west-2
```

### Deploy Frontend

```bash
cd frontend
npm run build

aws s3 sync dist/ s3://bluemoxon-frontend/ --profile bluemoxon --region us-west-2
aws cloudfront create-invalidation \
  --distribution-id E16BJX90QWQNQO \
  --paths "/*" \
  --profile bluemoxon
```

### Create Admin User

```bash
aws cognito-idp admin-create-user \
  --user-pool-id us-west-2_PvdIpXVKF \
  --username admin@bluemoxon.com \
  --user-attributes Name=email,Value=admin@bluemoxon.com \
  --temporary-password "TempPass123!" \
  --profile bluemoxon --region us-west-2
```

## URLs

| Environment | URL |
|-------------|-----|
| Frontend (Production) | https://bluemoxon.com |
| Frontend (CloudFront) | https://d2yd5bvqaomg54.cloudfront.net |
| API (Production) | https://h7q9ga51xa.execute-api.us-west-2.amazonaws.com |
| API Health Check | https://h7q9ga51xa.execute-api.us-west-2.amazonaws.com/health |
| Cognito Login | https://bluemoxon.auth.us-west-2.amazoncognito.com |

## Configuration File

All resource IDs are stored in: `infra/aws-resources.json`

---

*Last Updated: November 30, 2025*
