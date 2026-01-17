# Image Processor Container Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deploy image processor Lambda as ARM64 container with rembg for background removal.

**Architecture:** Container-based Lambda triggered by SQS, processes book images to remove backgrounds and add solid color based on brightness.

**Tech Stack:** Python 3.12, rembg, Pillow, Docker, ECR, Terraform, GitHub Actions

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Model packaging | Copy `backend/app/models/` into container | Single source of truth, no drift |
| Base image | `public.ecr.aws/lambda/python:3.12-arm64` | Official, Graviton2 saves 20% |
| rembg models | Baked into container | Instant cold starts |
| CI/CD | Extend Deploy workflow with conditionals | Consistent patterns |
| Deployment | CI updates Lambda directly, Terraform ignores | Simpler than passing image_uri |

---

## Section 1: Container Structure

**Directory layout:**
```
backend/lambdas/image_processor/
├── handler.py           # (exists) Main Lambda handler
├── Dockerfile           # (new) ARM64 container build
├── requirements.txt     # (new) rembg, pillow, sqlalchemy, boto3
├── download_models.py   # (new) Pre-download rembg models
└── tests/
    ├── conftest.py      # (new) Fixtures
    └── test_handler.py  # (new) Unit tests
```

**Dockerfile:**
```dockerfile
FROM public.ecr.aws/lambda/python:3.12-arm64

# Copy backend models (single source of truth)
COPY backend/app/__init__.py /opt/python/app/
COPY backend/app/models/ /opt/python/app/models/
ENV PYTHONPATH=/opt/python:$PYTHONPATH

# Install dependencies
COPY backend/lambdas/image_processor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download rembg models
COPY backend/lambdas/image_processor/download_models.py .
RUN python download_models.py && rm download_models.py

# Copy handler
COPY backend/lambdas/image_processor/handler.py ${LAMBDA_TASK_ROOT}/

CMD ["handler.lambda_handler"]
```

**requirements.txt:**
```
rembg[cpu]==2.0.50
pillow>=10.0.0
boto3>=1.28.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
```

**download_models.py:**
```python
"""Pre-download rembg models during Docker build."""
from rembg import new_session

print("Downloading u2net model...")
new_session("u2net")

print("Downloading isnet-general-use model...")
new_session("isnet-general-use")

print("Models downloaded successfully")
```

---

## Section 2: Terraform Changes

**New ECR repository** (`infra/terraform/ecr.tf`):
```hcl
resource "aws_ecr_repository" "image_processor" {
  name                 = "bluemoxon-image-processor"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "image_processor" {
  repository = aws_ecr_repository.image_processor.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Expire untagged images after 7 days"
      selection = {
        tagStatus   = "untagged"
        countType   = "sinceImagePushed"
        countUnit   = "days"
        countNumber = 7
      }
      action = { type = "expire" }
    }]
  })
}

output "image_processor_ecr_url" {
  value = aws_ecr_repository.image_processor.repository_url
}
```

**Lambda module changes** (`infra/terraform/modules/image-processor/main.tf`):
```hcl
resource "aws_lambda_function" "worker" {
  function_name = "${var.name_prefix}-image-processor"
  role          = aws_iam_role.worker_exec.arn
  package_type  = "Image"

  # Bootstrap fallback for initial creation
  image_uri     = var.image_uri != "" ? var.image_uri : "${var.ecr_repository_url}:latest"

  timeout       = var.timeout
  memory_size   = var.memory_size
  architectures = ["arm64"]

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = merge({
      ENVIRONMENT           = var.environment
      BMX_IMAGES_BUCKET     = var.images_bucket
      BMX_IMAGES_CDN_DOMAIN = var.images_cdn_domain
      DATABASE_SECRET_ARN   = var.database_secret_arn
    }, var.environment_variables)
  }

  dynamic "vpc_config" {
    for_each = length(var.vpc_subnet_ids) > 0 ? [1] : []
    content {
      subnet_ids         = var.vpc_subnet_ids
      security_group_ids = var.vpc_security_group_ids
    }
  }

  lifecycle {
    ignore_changes = [image_uri]  # CI updates directly
  }

  tags = {
    Environment = var.environment
    Service     = "image-processing"
  }
}
```

**Variables to remove:** `s3_bucket`, `s3_key`, `handler`, `runtime`
**Variables to add:** `image_uri`, `ecr_repository_url`

---

## Section 3: CI/CD Workflow

**Path filters** (add to `on:` block in deploy.yml):
```yaml
on:
  push:
    branches: [staging, main]
    paths:
      - 'backend/lambdas/image_processor/**'
      - 'backend/app/models/**'
      - '.github/workflows/deploy.yml'
```

**Test job:**
```yaml
test-image-processor:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: '3.12'
    - name: Run tests
      run: |
        cd backend/lambdas/image_processor
        pip install -r requirements.txt pytest pytest-mock
        pytest tests/ -v --cov=. --cov-fail-under=80
```

**Build job:**
```yaml
build-image-processor:
  name: Build Image Processor
  needs: [test-image-processor]
  runs-on: ubuntu-latest
  outputs:
    image_uri: ${{ steps.meta.outputs.tags }}

  steps:
    - uses: actions/checkout@v4

    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
        aws-region: us-west-2

    - name: Login to ECR
      uses: aws-actions/amazon-ecr-login@v2

    - name: Get ECR repository
      id: ecr
      run: |
        REPO_URL=$(aws ecr describe-repositories \
          --repository-names bluemoxon-image-processor \
          --query 'repositories[0].repositoryUri' \
          --output text)
        echo "url=$REPO_URL" >> $GITHUB_OUTPUT

    - name: Docker meta
      id: meta
      run: |
        TAGS="${{ steps.ecr.outputs.url }}:${{ github.sha }}"
        echo "tags=$TAGS" >> $GITHUB_OUTPUT

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Build and push
      uses: docker/build-push-action@v5
      with:
        context: .
        file: backend/lambdas/image_processor/Dockerfile
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        platforms: linux/arm64
        cache-from: type=registry,ref=${{ steps.ecr.outputs.url }}:buildcache
        cache-to: type=registry,ref=${{ steps.ecr.outputs.url }}:buildcache,mode=max
```

**Deploy jobs:**
```yaml
deploy-image-processor-staging:
  needs: [build-image-processor]
  if: always() && needs.build-image-processor.result == 'success' && github.ref == 'refs/heads/staging'
  runs-on: ubuntu-latest
  environment: staging

  steps:
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}
        aws-region: us-west-2

    - name: Update Lambda function
      run: |
        aws lambda update-function-code \
          --function-name bluemoxon-staging-image-processor \
          --image-uri ${{ needs.build-image-processor.outputs.image_uri }}

    - name: Wait for update
      run: |
        aws lambda wait function-updated-v2 \
          --function-name bluemoxon-staging-image-processor

    - name: Tag deployment
      run: |
        aws lambda tag-resource \
          --resource arn:aws:lambda:us-west-2:${{ vars.AWS_ACCOUNT_ID }}:function:bluemoxon-staging-image-processor \
          --tags DeployedCommit=${{ github.sha }},DeployedAt=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    - name: Smoke test
      run: |
        aws lambda invoke \
          --function-name bluemoxon-staging-image-processor \
          --payload '{"smoke_test": true}' \
          --log-type Tail \
          /tmp/response.json
        cat /tmp/response.json
        if grep -q "errorMessage" /tmp/response.json; then
          echo "Smoke test failed"
          exit 1
        fi

deploy-image-processor-prod:
  needs: [build-image-processor]
  if: always() && needs.build-image-processor.result == 'success' && github.ref == 'refs/heads/main'
  runs-on: ubuntu-latest
  environment: production  # Requires approval

  steps:
    # Same as staging with production function name
```

---

## Section 4: Testing Strategy

**Handler smoke test support** (add to handler.py):
```python
def lambda_handler(event, context):
    # Support smoke tests
    if event.get("smoke_test"):
        logger.info("Smoke test invocation")
        return {
            "statusCode": 200,
            "body": "OK",
            "version": os.environ.get("AWS_LAMBDA_FUNCTION_VERSION")
        }

    # Normal SQS processing
    # ... existing code
```

**Critical unit tests:**
```python
# test_handler.py

def test_smoke_test_returns_ok():
    result = lambda_handler({"smoke_test": True}, None)
    assert result["statusCode"] == 200

def test_sqs_event_parsing():
    """Handler correctly extracts job data from SQS message."""
    sqs_event = {
        "Records": [{
            "messageId": "msg-123",
            "body": json.dumps({
                "job_id": "job-456",
                "book_id": 123,
                "image_id": 789
            })
        }]
    }
    result = lambda_handler(sqs_event, None)
    assert "batchItemFailures" in result

def test_missing_image_fails_gracefully(mock_db_session):
    """Job marked failed when source image not found."""
    process_image(job_id="1", book_id=123, image_id=999)
    job = mock_db_session.query(ImageProcessingJob).get("1")
    assert job.status == "failed"

def test_job_status_completed_on_success(mock_db_session, mock_s3):
    process_image(job_id="1", book_id=123, image_id=456)
    job = mock_db_session.query(ImageProcessingJob).get("1")
    assert job.status == "completed"
    assert job.completed_at is not None

def test_brightness_selects_correct_background():
    assert select_background_color(100) == "black"
    assert select_background_color(200) == "white"

def test_quality_validation_rejects_small_subject():
    result = validate_image_quality(1000, 1000, 300, 300)
    assert result["passed"] is False
    assert result["reason"] == "area_too_small"
```

**Local testing with RIE:**
```bash
docker run -p 9000:8080 image-processor:local
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{"smoke_test": true}'
```

---

## Implementation Order

1. **Create ECR repository** (Terraform)
2. **Push bootstrap image** (manual, one-time)
3. **Update Lambda module** (Terraform - package_type, image_uri, architectures)
4. **Add supporting files** (Dockerfile, requirements.txt, download_models.py)
5. **Add smoke test handler** (handler.py modification)
6. **Add unit tests** (tests/)
7. **Update CI/CD workflow** (deploy.yml)
8. **Test end-to-end** (staging)
9. **Deploy to prod**

---

## First-Time Setup

```bash
# 1. Apply Terraform to create ECR
cd infra/terraform
terraform apply -target=aws_ecr_repository.image_processor

# 2. Build and push bootstrap image
aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.us-west-2.amazonaws.com
docker build -f backend/lambdas/image_processor/Dockerfile -t <ecr-url>:latest .
docker push <ecr-url>:latest

# 3. Apply full Terraform
terraform apply -var="image_uri=<ecr-url>:latest"

# 4. After this, CI takes over with SHA-tagged images
```
