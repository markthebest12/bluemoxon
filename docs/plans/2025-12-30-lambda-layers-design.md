# Lambda Layers Design Document

**Date:** 2025-12-30
**Status:** Ready for Implementation
**Author:** Claude (with Mark)

---

## Problem Statement

The BlueMoxon Lambda deployment packages are approaching the AWS Lambda size limit (~66MB for direct upload, 250MB unzipped). The current monolithic approach bundles all Python dependencies with every deploy, even when only application code changes.

**Current pain points:**
1. Cleanup Lambda creation failed with `RequestEntityTooLargeException` (72MB > 66MB)
2. Every deploy rebuilds the full 50MB package even for 1-line code changes
3. No code sharing between Lambda functions (API, cleanup, db-sync, eval-runbook-worker)
4. Risk of hitting size limits as dependencies grow

---

## Solution: Lambda Layers

Split the Lambda deployment into two parts:

1. **Dependencies Layer (~50MB):** All Python packages from `requirements.txt`
2. **Function Code (<1MB):** Application code (`app/`, `lambdas/`)

### Benefits

| Aspect | Before | After |
|--------|--------|-------|
| Package size | ~50MB | <1MB function + 50MB layer |
| Deploy time | ~3 min (rebuild all) | <30 sec (code only) |
| Layer updates | Every deploy | Only when `poetry.lock` changes |
| Code sharing | None | Layer shared across all Lambdas |
| Size headroom | At limit | ~200MB remaining |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         S3 Bucket                                │
│  s3://bluemoxon-frontend-{env}/lambda/                          │
│  ├── layer.zip          (50MB - Python dependencies)            │
│  ├── layer-{hash}.zip   (versioned by poetry.lock hash)         │
│  ├── backend.zip        (<1MB - app/ + lambdas/ + VERSION)      │
│  └── cleanup.zip        (<1MB - same code, different entry)     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Lambda Layer                                  │
│  bluemoxon-{env}-deps                                           │
│  └── python/           (layer directory structure)              │
│      ├── boto3/                                                 │
│      ├── sqlalchemy/                                            │
│      ├── httpx/                                                 │
│      ├── pydantic/                                              │
│      └── ... (all dependencies)                                 │
└─────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│   API Lambda             │  │   Cleanup Lambda         │
│   bluemoxon-{env}-api    │  │   bluemoxon-{env}-cleanup│
│   ├── app/               │  │   ├── app/               │
│   ├── lambdas/           │  │   ├── lambdas/           │
│   └── VERSION            │  │   └── VERSION            │
│                          │  │                          │
│   Handler: app.main      │  │   Handler: lambdas...    │
│   Layer: deps            │  │   Layer: deps            │
└──────────────────────────┘  └──────────────────────────┘
```

---

## Layer Directory Structure

Lambda Layers require a specific directory structure. For Python:

```
layer.zip
└── python/
    ├── boto3/
    ├── botocore/
    ├── sqlalchemy/
    ├── httpx/
    ├── pydantic/
    ├── ... (all packages)
    └── *.dist-info/  (keep for importlib.metadata)
```

The `python/` prefix is required - Lambda adds `/opt/python` to `PYTHONPATH`.

---

## CI/CD Workflow Changes

### Current Flow
```
build-backend → upload backend.zip → update Lambda code
```

### New Flow
```
build-layer ────────────┐
  (if poetry.lock       │
   changed)             ├──→ deploy-backend
                        │      - publish layer version
build-backend ──────────┘      - update Lambda code
  (app/ + lambdas/)            - update Lambda config (layers)
```

### Layer Caching Strategy

To avoid rebuilding the layer on every deploy:

1. Hash the `poetry.lock` file: `LOCK_HASH=$(sha256sum poetry.lock | cut -c1-16)`
2. Check if `layer-{LOCK_HASH}.zip` exists in S3
3. If exists, skip build
4. If not, build and upload as `layer-{LOCK_HASH}.zip` AND `layer.zip`

The `layer.zip` is always the latest for Terraform reference. The hash-versioned files enable caching.

---

## Terraform Changes

### New Module: `modules/lambda-layer/`

```hcl
resource "aws_lambda_layer_version" "this" {
  layer_name          = var.layer_name
  description         = var.description
  compatible_runtimes = ["python3.12"]
  s3_bucket           = var.s3_bucket
  s3_key              = var.s3_key

  lifecycle {
    ignore_changes = [s3_key]  # CI/CD manages versions
  }
}
```

### Lambda Module Updates

Add `layers` variable and pass to `aws_lambda_function`:

```hcl
variable "layers" {
  type    = list(string)
  default = []
}

resource "aws_lambda_function" "this" {
  # ... existing config ...
  layers = var.layers

  lifecycle {
    ignore_changes = [filename, source_code_hash, layers]
  }
}
```

### Main Config Wiring

```hcl
module "lambda_layer" {
  source     = "./modules/lambda-layer"
  layer_name = "bluemoxon-${var.environment}-deps"
  s3_bucket  = module.s3.frontend_bucket_id
  s3_key     = "lambda/layer.zip"
}

module "lambda" {
  # ... existing config ...
  layers = [module.lambda_layer.layer_version_arn]
}
```

---

## Deploy Workflow Pseudocode

```yaml
build-layer:
  steps:
    - checkout
    - hash = sha256(poetry.lock)[0:16]
    - if s3_exists("layer-{hash}.zip"):
        skip build
      else:
        docker run:
          pip install -t /output/python -r requirements.txt
        zip -r layer.zip python
        s3 cp layer.zip layer-{hash}.zip
        s3 cp layer.zip layer.zip  # for terraform

build-backend:
  steps:
    - checkout
    - docker run:
        cp -r app/ lambdas/ VERSION /output/
    - zip -r backend.zip .
    - upload artifact

deploy-backend:
  needs: [build-layer, build-backend]
  steps:
    - download backend.zip
    - s3 cp backend.zip
    - layer_arn = lambda publish-layer-version (if layer changed)
    - lambda update-function-code (backend.zip)
    - lambda update-function-configuration --layers $layer_arn
```

---

## Function Package Contents

**Before (50MB):**
```
lambda-package.zip
├── app/                    (~100KB)
├── boto3/                  (~5MB)
├── botocore/               (~40MB)
├── sqlalchemy/             (~2MB)
├── httpx/                  (~500KB)
├── pydantic/               (~1MB)
├── ... (many more packages)
└── VERSION
```

**After (<1MB):**
```
backend.zip
├── app/                    (~100KB)
├── lambdas/                (~10KB)
│   ├── __init__.py
│   ├── cleanup/
│   │   ├── __init__.py
│   │   └── handler.py
│   └── db_sync/
│       └── ...
└── VERSION
```

---

## Environment Handling

**Single shared layer per environment:**
- `bluemoxon-staging-deps` - staging layer
- `bluemoxon-prod-deps` - production layer

Both environments use the same `poetry.lock`, so layers are functionally identical. Separate layers allow independent versioning if needed.

---

## Rollback Strategy

Lambda Layer versions are immutable. Rollback options:

1. **Code rollback:** Update Lambda to use previous code zip (standard)
2. **Layer rollback:** Update Lambda to reference previous layer version ARN
3. **Full rollback:** Both code and layer version

Layer versions are retained indefinitely. Old versions can be deleted via:
```bash
aws lambda delete-layer-version --layer-name bluemoxon-staging-deps --version-number N
```

---

## Migration Plan

### Phase 1: Create Layer Infrastructure
1. Create `modules/lambda-layer/` Terraform module
2. Add `layers` variable to `modules/lambda/`
3. Wire up in `main.tf`
4. Apply Terraform (creates layer resource, doesn't affect running Lambdas)

### Phase 2: Bootstrap Layer
1. Build layer locally (or in CI)
2. Upload to S3
3. Publish initial layer version
4. Update existing Lambdas to use layer (manual first time)

### Phase 3: Update CI/CD
1. Add `build-layer` job to deploy workflow
2. Modify `build-backend` to exclude dependencies
3. Add layer publish and attach steps to `deploy-backend`

### Phase 4: Verify and Cleanup
1. Test all Lambda functions work with layer
2. Verify deploys work end-to-end
3. Delete manual IAM policy (replaced by Terraform)
4. Promote to production

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `infra/terraform/modules/lambda-layer/main.tf` | Create | Layer Terraform resource |
| `infra/terraform/modules/lambda-layer/variables.tf` | Create | Layer variables |
| `infra/terraform/modules/lambda-layer/outputs.tf` | Create | Layer outputs |
| `infra/terraform/modules/lambda-layer/versions.tf` | Create | Provider versions |
| `infra/terraform/modules/lambda/variables.tf` | Modify | Add `layers` variable |
| `infra/terraform/modules/lambda/main.tf` | Modify | Add `layers` to function |
| `infra/terraform/modules/cleanup-lambda/variables.tf` | Modify | Add `layers` variable |
| `infra/terraform/modules/cleanup-lambda/main.tf` | Modify | Add `layers` to function |
| `infra/terraform/main.tf` | Modify | Add layer module, wire to lambdas |
| `.github/workflows/deploy.yml` | Modify | Add layer build/publish steps |
| `.github/workflows/deploy-staging.yml` | Modify | Same changes for staging |

---

## Testing Checklist

- [ ] Layer builds successfully in Docker
- [ ] Layer uploads to S3
- [ ] Layer publishes to Lambda
- [ ] API Lambda imports all dependencies
- [ ] Cleanup Lambda imports all dependencies
- [ ] API endpoints work (auth, books, images)
- [ ] Cleanup endpoint works
- [ ] CI/CD pipeline completes successfully
- [ ] Layer caching works (skips rebuild when unchanged)
- [ ] Rollback procedure verified

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Layer incompatible with Lambda runtime | Functions fail to start | Use same Docker image for build and runtime |
| Layer too large (>50MB zipped) | Can't publish | Prune unnecessary packages from requirements |
| CI/CD breaks during migration | Deploys fail | Keep old workflow, feature flag new behavior |
| Missing package in layer | Import errors | Run full test suite before production |

---

## Open Questions (Resolved)

1. **Shared vs per-environment layers?** → Shared per environment (staging/prod separate)
2. **How to handle layer versioning?** → Hash poetry.lock, cache in S3
3. **What about Lambda functions outside this workflow?** → Scraper uses Docker image, unaffected

---

## Success Criteria

1. ✅ Lambda packages < 1MB (excluding layer)
2. ✅ Layer builds only when dependencies change
3. ✅ All Lambda functions work with shared layer
4. ✅ CI/CD pipeline unchanged from user perspective
5. ✅ Deploy time reduced (code-only deploys < 30 seconds)
