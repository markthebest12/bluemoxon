# Image Processor Container Implementation Plan

> **Status:** ✅ IMPLEMENTED - E2E tested in staging (2026-01-17)
> **For Claude:** This plan has been executed. See session log for implementation details.

**Goal:** Deploy image processor Lambda as container with rembg for background removal.

**Architecture:** Container-based Lambda triggered by SQS, processes book images to remove backgrounds and add solid color based on brightness.

**Tech Stack:** Python 3.12, rembg, Pillow, Docker, ECR, Terraform, GitHub Actions

---

## Design Decisions (Updated Post-Implementation)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Architecture | **x86_64** | ONNX Runtime crashes on ARM64 Lambda (cpuinfo parsing failure) |
| Model packaging | Copy `backend/app/models/` + `constants.py` into container | Single source of truth, model imports cascade |
| Base image | `public.ecr.aws/lambda/python:3.12` | Official x86_64 image |
| rembg models | Baked into `/opt/u2net` | Instant cold starts, Lambda home is read-only |
| Memory | 10240 MB (staging), 3072 MB (default) | u2net needs ~6.2 GB |
| CI/CD | Extend Deploy workflow with conditionals | Consistent patterns |
| Deployment | CI updates Lambda directly, Terraform ignores | Simpler than passing image_uri |

---

## Section 1: Container Structure (IMPLEMENTED)

**Directory layout:**
```
backend/lambdas/image_processor/
├── handler.py           # Main Lambda handler with lazy rembg loading
├── Dockerfile           # x86_64 container build
├── requirements.txt     # rembg[cpu]>=2.0.55, pillow, sqlalchemy, boto3
├── download_models.py   # Pre-download rembg models to /opt/u2net
└── tests/
    ├── conftest.py      # Fixtures
    └── test_handler.py  # 30 unit tests
```

**Dockerfile (ACTUAL):**
```dockerfile
# Note: Using x86_64 because ONNX Runtime crashes on ARM64 Lambda due to cpuinfo parsing failure
# See: https://github.com/microsoft/onnxruntime/issues/10038
FROM public.ecr.aws/lambda/python:3.12

# Accept VERSION as build argument (default to dev for local builds)
ARG VERSION=0.0.0-dev

# Copy backend models (single source of truth) and dependencies
COPY backend/app/__init__.py /opt/python/app/
COPY backend/app/constants.py /opt/python/app/   # IMPORTANT: models import constants
COPY backend/app/models/ /opt/python/app/models/

# Make models readable by Lambda's sandbox user
RUN chmod -R 755 /opt/python

# Bake VERSION into image for tracking
RUN echo "$VERSION" > /opt/python/VERSION

ENV PYTHONPATH=/opt/python:$PYTHONPATH

# Install dependencies
COPY backend/lambdas/image_processor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download rembg models to /opt/u2net (readable at runtime)
# Note: Must set U2NET_HOME at runtime to match this path
ENV U2NET_HOME=/opt/u2net
COPY backend/lambdas/image_processor/download_models.py .
RUN python download_models.py
RUN rm download_models.py
RUN chmod -R 755 /opt/u2net

# Copy handler
COPY backend/lambdas/image_processor/handler.py ${LAMBDA_TASK_ROOT}/

# Switch to non-root user for security scanning compliance
# Note: Lambda overrides this at runtime with its own sandbox user
USER 1000

CMD ["handler.lambda_handler"]
```

**requirements.txt (ACTUAL):**
```
rembg[cpu]>=2.0.55
pillow>=10.0.0
boto3>=1.28.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
```

---

## Section 2: Terraform Changes (IMPLEMENTED)

**Lambda environment variables (ACTUAL):**
```hcl
environment {
  variables = merge({
    ENVIRONMENT         = var.environment
    IMAGES_BUCKET       = var.images_bucket       # NOT BMX_IMAGES_BUCKET
    IMAGES_CDN_DOMAIN   = var.images_cdn_domain   # NOT BMX_IMAGES_CDN_DOMAIN
    DATABASE_SECRET_ARN = var.database_secret_arn
    # Numba cache dir for pymatting JIT compilation (Lambda filesystem is read-only)
    NUMBA_CACHE_DIR = "/tmp"
    # rembg model location (pre-downloaded in container image)
    U2NET_HOME = "/opt/u2net"
  }, var.environment_variables)
}
```

**Lambda configuration (ACTUAL):**
```hcl
resource "aws_lambda_function" "worker" {
  function_name = "${var.name_prefix}-image-processor"
  role          = aws_iam_role.worker_exec.arn
  package_type  = "Image"

  image_uri = var.image_uri != "" ? var.image_uri : "${var.ecr_repository_url}:${var.image_tag}"

  timeout       = var.timeout        # 300 seconds
  memory_size   = var.memory_size    # 3072 MB default (needs 6.2GB for u2net)
  # Note: Using x86_64 because ONNX Runtime crashes on ARM64 Lambda
  architectures = ["x86_64"]

  reserved_concurrent_executions = var.reserved_concurrency

  # ... environment, vpc_config, etc.

  lifecycle {
    ignore_changes = [image_uri]  # CI updates directly
  }
}
```

---

## Section 3: Critical Discoveries from E2E Testing

### 1. ONNX Runtime ARM64 Incompatibility
- **Error:** `onnxruntime::OnnxRuntimeException: Attempt to use DefaultLogger but none has been registered`
- **Root cause:** cpuinfo parsing fails on Lambda Graviton2
- **Solution:** Use x86_64 architecture

### 2. Lambda Read-Only Filesystem
- **Error:** `[Errno 30] Read-only file system: '/home/sbx_user1051'`
- **Root cause:** rembg tries to download models to `~/.u2net/`
- **Solution:** Set `U2NET_HOME=/opt/u2net` in Dockerfile and Lambda env

### 3. Numba JIT Cache
- **Error:** `cannot cache function '_make_tree': no locator available`
- **Root cause:** pymatting Numba JIT tries to cache in read-only location
- **Solution:** Set `NUMBA_CACHE_DIR=/tmp`

### 4. Memory Requirements
- **Observation:** u2net model requires ~6.2 GB memory
- **Solution:** Set memory to 10240 MB for staging, 3072 MB default (may need increase in prod)

### 5. S3 Key Prefix Handling
- **Issue:** API adds `books/` prefix via `S3_IMAGES_PREFIX`
- **Solution:** Handler stores `db_s3_key` (without prefix) in DB, uses `full_s3_key` (with prefix) for S3 upload

### 6. Model Import Dependencies
- **Issue:** `app.models` imports from `app.constants`
- **Solution:** Copy `constants.py` into container alongside models

---

## Implementation Order (COMPLETED)

| Step | Status | Commit |
|------|--------|--------|
| 1. Create ECR repository | ✅ Done | `1d6a348` |
| 2. Add supporting files | ✅ Done | `0a91d34` |
| 3. Add smoke test handler | ✅ Done | `164ac27` |
| 4. Push bootstrap image | ✅ Done | `839aba9` |
| 5. Update Lambda module | ✅ Done | `25c10fb` |
| 6. Add unit tests (30 passing) | ✅ Done | `b39628f` |
| 7. Update CI/CD workflow | ✅ Done | `078aca5` |
| 8. Test end-to-end in staging | ✅ Done | `5829d22` |
| 9. Deploy to production | ⏳ Pending | After staging PR |

---

## Key Lessons Learned

1. **ARM64 package availability differs** - check PyPI for architecture-specific packages
2. **ONNX Runtime cpuinfo crash on ARM64** - use x86_64 for Lambda
3. **Lambda home directory is read-only** - set model paths to `/opt/` or `/tmp/`
4. **Numba JIT needs writable cache** - set `NUMBA_CACHE_DIR=/tmp`
5. **rembg memory requirements** - u2net needs ~6.2 GB RAM
6. **Model imports cascade** - copy all transitive dependencies into container
7. **S3 key prefixes** - be consistent between handler and API code

---

## Related Files

| File | Purpose |
|------|---------|
| `backend/lambdas/image_processor/handler.py` | Lambda handler |
| `backend/lambdas/image_processor/Dockerfile` | Container build |
| `infra/terraform/modules/image-processor/main.tf` | Lambda module |
| `infra/terraform/modules/image-processor/variables.tf` | Module variables |
| `.github/workflows/deploy.yml` | CI/CD workflow |
| `docs/sessions/2026-01-16-auto-process-images.md` | Session log |
