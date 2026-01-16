# Cleanup Lambda Design

**Date**: 2025-12-29
**Issues**: #189, #190, #191
**Status**: Approved

## Overview

Maintenance system for cleaning up stale acquisitions data, expired source URLs, orphaned S3 images, and retrying failed Wayback archives.

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Deployment | Standalone Lambda | Separate timeout limits (5 min), follows db_sync/eval_worker pattern |
| DB Access | Reuse app.models | Type-safe ORM queries, consistent with eval_worker |
| Orphan Cleanup | Dry-run default | Irreversible deletion requires explicit confirmation |
| Scheduling | Manual only | Low-priority maintenance, admin triggers via UI |
| Archive Retries | Max 3 attempts | Prevents infinite retries on permanently unavailable URLs |

## Component Design

### 1. Cleanup Lambda (#189)

**Location**: `backend/lambdas/cleanup/`

```text
backend/lambdas/cleanup/
├── handler.py
├── requirements.txt
└── __init__.py
```

**Handler Interface**:

```python
def handler(event: dict, context) -> dict:
    """Cleanup Lambda handler.

    Event payload:
        action: "all" | "stale" | "expired" | "orphans" | "archives"
        delete_orphans: bool (default False)

    Returns:
        {
            "statusCode": 200,
            "body": {
                "stale_archived": int,
                "sources_checked": int,
                "sources_expired": int,
                "orphans_found": int,
                "orphans_deleted": int,
                "archives_retried": int,
                "archives_succeeded": int,
                "duration_seconds": float,
                "errors": list[str]
            }
        }
    """
```

**Operations**:

1. **cleanup_stale_evaluations(db: Session) -> int**
   - Query: `Book.status == 'EVALUATING' AND Book.updated_at < now() - 30 days`
   - Action: Set `status = 'REMOVED'`
   - Returns: Count of archived books

2. **check_expired_sources(db: Session) -> tuple[int, int]**
   - Query: Books with `source_url IS NOT NULL AND source_expired IS NULL`
   - Action: HEAD request each URL, set `source_expired = True` if 404/410/unavailable
   - Returns: (checked_count, expired_count)

3. **cleanup_orphaned_images(db: Session, delete: bool = False) -> dict**
   - List all keys in S3 images bucket
   - Query all `Book.images` arrays from DB
   - Diff to find orphaned S3 keys
   - If `delete=True`: Delete orphaned keys from S3
   - Returns: `{"found": int, "deleted": int, "keys": list[str]}`

4. **retry_failed_archives(db: Session) -> dict**
   - Query: `Book.archive_status == 'failed' AND Book.archive_attempts < 3`
   - Action: Call `archive_url()`, update status and increment attempts
   - Returns: `{"retried": int, "succeeded": int, "failed": int}`

### 2. Admin API Endpoint (#190)

**Location**: `backend/app/api/v1/admin.py`

```python
class CleanupRequest(BaseModel):
    action: Literal["all", "stale", "expired", "orphans", "archives"] = "all"
    delete_orphans: bool = False

class CleanupResult(BaseModel):
    stale_archived: int = 0
    sources_checked: int = 0
    sources_expired: int = 0
    orphans_found: int = 0
    orphans_deleted: int = 0
    archives_retried: int = 0
    archives_succeeded: int = 0
    duration_seconds: float = 0
    errors: list[str] = []

@router.post("/cleanup", response_model=CleanupResult)
def run_cleanup(
    request: CleanupRequest,
    _user=Depends(require_admin),
):
    """Invoke cleanup Lambda (admin only).

    Uses boto3 Lambda invoke with RequestResponse for synchronous execution.
    Lambda name: bluemoxon-{env}-cleanup
    """
```

### 3. Frontend Cleanup Panel (#191)

**Location**: `frontend/src/views/AcquisitionsView.vue`

- Collapsible "Cleanup Tools" panel at bottom of view
- Only visible to admin users (`v-if="authStore.isAdmin"`)
- Buttons for each cleanup action
- Orphans: Separate "Scan" and "Delete" buttons
- Results displayed in toast/notification
- Loading state disables buttons during operation

### 4. Database Migration

**New field on Book model**:

```python
archive_attempts: Mapped[int] = mapped_column(Integer, default=0)
```

**Migration**:

```python
def upgrade():
    op.add_column('books', sa.Column('archive_attempts', sa.Integer(),
                                      nullable=False, server_default='0'))
```

### 5. Terraform Infrastructure

**New module**: `infra/terraform/modules/cleanup-lambda/`

```hcl
resource "aws_lambda_function" "cleanup" {
  function_name = "${var.project}-${var.environment}-cleanup"
  runtime       = "python3.12"
  handler       = "handler.handler"
  timeout       = 300  # 5 minutes
  memory_size   = 256

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [var.lambda_security_group_id]
  }

  environment {
    variables = {
      DATABASE_SECRET_ARN = var.database_secret_arn
      IMAGES_BUCKET       = var.images_bucket
      ENVIRONMENT         = var.environment
    }
  }
}
```

**IAM Permissions**:

- Secrets Manager: Read database credentials
- S3: ListBucket, DeleteObject on images bucket
- CloudWatch: CreateLogGroup, CreateLogStream, PutLogEvents
- VPC: Network interface management

## Implementation Order

1. **Database migration** - Add `archive_attempts` field
2. **Cleanup Lambda** - Core cleanup functions with tests
3. **Terraform module** - Lambda infrastructure
4. **Admin API endpoint** - POST /admin/cleanup
5. **Frontend panel** - Cleanup tools UI

## Testing Strategy

- Unit tests for each cleanup function with mocked DB/S3
- Integration tests with test database
- Manual testing in staging before production

## Rollback Plan

- Lambda can be disabled by removing invoke permissions
- Migration is additive (new column), safe to roll forward
- Frontend panel is admin-only, low risk
