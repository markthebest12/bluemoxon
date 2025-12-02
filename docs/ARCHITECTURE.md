# BlueMoxon Architecture

## System Overview

```
Route 53 (bluemoxon.com)
    │
    ├── CloudFront ──> S3 (Vue 3 SPA)
    │
    └── CloudFront ──> API Gateway ──> Lambda (FastAPI + Mangum)
                                            │
                                    ┌───────┴───────┐
                                    │  Private VPC  │
                                    │ Aurora Sv2    │
                                    │ (PostgreSQL)  │
                                    └───────────────┘

Additional Services:
- Cognito User Pool (MFA required, admin invite only)
- S3 Bucket (book images with CloudFront CDN)
- Secrets Manager (DB credentials)
- CodePipeline + CodeBuild (CI/CD)
```

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Compute | AWS Lambda | Cost-effective for low traffic, cold starts acceptable |
| Database | Aurora Serverless v2 | PostgreSQL for full-text search, scales to zero |
| Auth | Cognito + MFA | Managed auth, built-in 2FA, admin invite only |
| Frontend | Vue 3 + Vite | User preference, modern tooling |
| Backend | FastAPI | Fast, modern Python, auto-generated docs |
| IaC | AWS CDK (Python) | Type-safe, same language as backend |

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

## CDK Stacks

1. **NetworkStack** - VPC with public/private subnets
2. **DatabaseStack** - Aurora Serverless v2 PostgreSQL
3. **AuthStack** - Cognito User Pool with MFA
4. **StorageStack** - S3 buckets for frontend and images
5. **ApiStack** - Lambda + API Gateway
6. **FrontendStack** - S3 + CloudFront distribution
7. **DnsStack** - Route 53 hosted zone and records
8. **PipelineStack** - CodePipeline CI/CD

## Security

- **Authentication:** Cognito with required TOTP MFA
- **Authorization:** Role-based (admin/editor/viewer)
- **Encryption:** Aurora and S3 encrypted at rest
- **Network:** Aurora in isolated subnets, Lambda in private subnets
- **Transit:** HTTPS enforced via CloudFront
- **API:** JWT validation, Pydantic input validation, rate limiting

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

### Authentication Flows

```
User Invitation Flow:
Admin invites → Cognito sends email → User logs in with temp password
→ NEW_PASSWORD_REQUIRED challenge → User sets new password
→ MFA_SETUP challenge → User scans QR code → Access granted

Password Requirements (as of Dec 2024):
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- No special character requirement
```

### Role-Based Access

| Feature | Viewer | Editor | Admin |
|---------|--------|--------|-------|
| View books/images | ✓ | ✓ | ✓ |
| Edit books/analyses | ✗ | ✓ | ✓ |
| Upload/reorder images | ✗ | ✓ | ✓ |
| User management | ✗ | ✗ | ✓ |
| API key management | ✗ | ✗ | ✓ |
