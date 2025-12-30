# Lambda Layers Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Split Lambda deployment into a shared dependencies layer (~50MB) and small function code (<1MB), enabling faster deploys and staying under size limits.

**Architecture:** Create a shared Lambda Layer for Python dependencies (boto3, sqlalchemy, httpx, etc.). Function code (app/, lambdas/) deploys separately. Layer is shared across all Python Lambdas (API, cleanup, db-sync, eval-runbook-worker). Layer updates only when poetry.lock changes.

**Tech Stack:** AWS Lambda Layers, Terraform, GitHub Actions, Python 3.12

---

## Task 1: Create Lambda Layer Terraform Module

**Files:**
- Create: `infra/terraform/modules/lambda-layer/main.tf`
- Create: `infra/terraform/modules/lambda-layer/variables.tf`
- Create: `infra/terraform/modules/lambda-layer/outputs.tf`
- Create: `infra/terraform/modules/lambda-layer/versions.tf`

**Step 1: Create versions.tf**

```hcl
# infra/terraform/modules/lambda-layer/versions.tf
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}
```

**Step 2: Create variables.tf**

```hcl
# infra/terraform/modules/lambda-layer/variables.tf
variable "layer_name" {
  description = "Name of the Lambda layer"
  type        = string
}

variable "description" {
  description = "Description of the layer"
  type        = string
  default     = "Python dependencies layer"
}

variable "compatible_runtimes" {
  description = "List of compatible Lambda runtimes"
  type        = list(string)
  default     = ["python3.12"]
}

variable "s3_bucket" {
  description = "S3 bucket containing the layer zip"
  type        = string
}

variable "s3_key" {
  description = "S3 key for the layer zip"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
```

**Step 3: Create main.tf**

```hcl
# infra/terraform/modules/lambda-layer/main.tf
resource "aws_lambda_layer_version" "this" {
  layer_name          = var.layer_name
  description         = var.description
  compatible_runtimes = var.compatible_runtimes
  s3_bucket           = var.s3_bucket
  s3_key              = var.s3_key

  lifecycle {
    # Layer versions are immutable - CI/CD publishes new versions
    ignore_changes = [s3_key]
  }
}
```

**Step 4: Create outputs.tf**

```hcl
# infra/terraform/modules/lambda-layer/outputs.tf
output "layer_arn" {
  description = "ARN of the Lambda layer (without version)"
  value       = aws_lambda_layer_version.this.layer_arn
}

output "layer_version_arn" {
  description = "ARN of the Lambda layer version"
  value       = aws_lambda_layer_version.this.arn
}

output "layer_version" {
  description = "Version number of the layer"
  value       = aws_lambda_layer_version.this.version
}
```

**Step 5: Commit**

```bash
git add infra/terraform/modules/lambda-layer/
git commit -m "feat: add lambda-layer Terraform module"
```

---

## Task 2: Update Lambda Module to Support Layers

**Files:**
- Modify: `infra/terraform/modules/lambda/variables.tf`
- Modify: `infra/terraform/modules/lambda/main.tf`

**Step 1: Add layer variable to variables.tf**

Add after existing variables:

```hcl
variable "layers" {
  description = "List of Lambda Layer ARNs to attach"
  type        = list(string)
  default     = []
}
```

**Step 2: Update main.tf Lambda resource**

In the `aws_lambda_function.this` resource, add after `source_code_hash`:

```hcl
  layers = var.layers
```

And update the lifecycle block to ignore layers (managed by CI/CD):

```hcl
  lifecycle {
    ignore_changes = [
      filename,
      source_code_hash,
      layers,
    ]
  }
```

**Step 3: Commit**

```bash
git add infra/terraform/modules/lambda/
git commit -m "feat: add layers support to lambda module"
```

---

## Task 3: Wire Up Layer in Main Terraform Config

**Files:**
- Modify: `infra/terraform/main.tf`

**Step 1: Add layer module**

Add near the top, after locals:

```hcl
# =============================================================================
# Lambda Layer (shared Python dependencies)
# =============================================================================

module "lambda_layer" {
  source = "./modules/lambda-layer"

  layer_name  = "bluemoxon-${var.environment}-deps"
  description = "Shared Python dependencies for BlueMoxon Lambdas"
  s3_bucket   = module.s3.frontend_bucket_id
  s3_key      = "lambda/layer.zip"

  tags = local.common_tags
}
```

**Step 2: Pass layer ARN to lambda module**

Find the `module "lambda"` block and add:

```hcl
  layers = [module.lambda_layer.layer_version_arn]
```

**Step 3: Pass layer ARN to cleanup-lambda module**

Find the cleanup lambda module call and add layers variable (if not already supported, add to that module too).

**Step 4: Commit**

```bash
git add infra/terraform/main.tf
git commit -m "feat: wire lambda layer to API and cleanup functions"
```

---

## Task 4: Update Deploy Workflow - Build Layer Separately

**Files:**
- Modify: `.github/workflows/deploy.yml`

**Step 1: Add build-layer job**

Add after `generate-version` job, before `build-backend`:

```yaml
  # ============================================
  # Build Lambda Layer (dependencies only)
  # ============================================

  build-layer:
    name: Build Lambda Layer
    runs-on: ubuntu-latest
    needs: [ci, configure]

    steps:
      - uses: actions/checkout@v6

      - name: Check if layer needs rebuild
        id: layer-check
        run: |
          # Get poetry.lock hash
          LOCK_HASH=$(sha256sum backend/poetry.lock | cut -d' ' -f1 | head -c 16)
          echo "lock_hash=$LOCK_HASH" >> $GITHUB_OUTPUT

          # Check if layer already exists in S3
          if aws s3 ls "s3://${{ needs.configure.outputs.s3_frontend_bucket }}/lambda/layer-${LOCK_HASH}.zip" 2>/dev/null; then
            echo "exists=true" >> $GITHUB_OUTPUT
            echo "Layer already exists for this poetry.lock"
          else
            echo "exists=false" >> $GITHUB_OUTPUT
            echo "Layer needs to be built"
          fi

      - name: Build layer with Docker
        if: steps.layer-check.outputs.exists == 'false'
        run: |
          docker run --rm \
            --entrypoint /bin/bash \
            -v ${{ github.workspace }}/backend:/app:ro \
            -v /tmp/layer-build:/output \
            --platform linux/amd64 \
            public.ecr.aws/lambda/python:3.12 \
            -c "
              mkdir -p /output/python
              pip install -q -t /output/python -r /app/requirements.txt
            "

      - name: Create layer zip
        if: steps.layer-check.outputs.exists == 'false'
        run: |
          cd /tmp/layer-build
          zip -q -r ${{ github.workspace }}/layer.zip python \
            -x "*.pyc" -x "*__pycache__*"
          ls -lh ${{ github.workspace }}/layer.zip

      - name: Upload layer to S3
        if: steps.layer-check.outputs.exists == 'false'
        run: |
          LOCK_HASH=${{ steps.layer-check.outputs.lock_hash }}
          aws s3 cp layer.zip \
            s3://${{ needs.configure.outputs.s3_frontend_bucket }}/lambda/layer-${LOCK_HASH}.zip
          # Also copy to layer.zip for Terraform reference
          aws s3 cp layer.zip \
            s3://${{ needs.configure.outputs.s3_frontend_bucket }}/lambda/layer.zip

    outputs:
      layer_s3_key: lambda/layer-${{ steps.layer-check.outputs.lock_hash }}.zip
```

**Step 2: Update build-backend to exclude dependencies**

Replace the Docker build command:

```yaml
      - name: Build Lambda package with Docker
        run: |
          docker run --rm \
            --entrypoint /bin/bash \
            -v ${{ github.workspace }}/backend:/app:ro \
            -v ${{ github.workspace }}/VERSION:/VERSION:ro \
            -v ${{ github.workspace }}/version_info.json:/version_info.json:ro \
            -v /tmp/lambda-deploy:/output \
            --platform linux/amd64 \
            public.ecr.aws/lambda/python:3.12 \
            -c "
              # Copy application code only (no dependencies - in layer)
              cp -r /app/app /output/
              cp -r /app/lambdas /output/
              cp /VERSION /output/
              cp /version_info.json /output/
            "
```

**Step 3: Add build-layer to deploy-backend needs**

Update the `deploy-backend` job:

```yaml
  deploy-backend:
    name: Deploy Backend
    runs-on: ubuntu-latest
    needs: [configure, build-backend, build-layer, generate-version]
```

**Step 4: Add layer update step in deploy-backend**

After uploading the code, add layer update:

```yaml
      - name: Publish new layer version
        run: |
          LAYER_ARN=$(aws lambda publish-layer-version \
            --layer-name bluemoxon-${{ needs.configure.outputs.environment }}-deps \
            --content S3Bucket=${{ needs.configure.outputs.s3_frontend_bucket }},S3Key=${{ needs.build-layer.outputs.layer_s3_key }} \
            --compatible-runtimes python3.12 \
            --query 'LayerVersionArn' \
            --output text)
          echo "Published layer: $LAYER_ARN"
          echo "layer_arn=$LAYER_ARN" >> $GITHUB_OUTPUT

      - name: Update Lambda functions with new layer
        run: |
          LAYER_ARN=${{ steps.publish-layer.outputs.layer_arn }}

          # Update API Lambda
          aws lambda update-function-configuration \
            --function-name ${{ needs.configure.outputs.lambda_function_name }} \
            --layers "$LAYER_ARN"

          # Update cleanup Lambda (if exists)
          aws lambda update-function-configuration \
            --function-name bluemoxon-${{ needs.configure.outputs.environment }}-cleanup \
            --layers "$LAYER_ARN" 2>/dev/null || true
```

**Step 5: Commit**

```bash
git add .github/workflows/deploy.yml
git commit -m "feat: implement Lambda Layers in deploy workflow"
```

---

## Task 5: Update Cleanup Lambda Module for Layers

**Files:**
- Modify: `infra/terraform/modules/cleanup-lambda/variables.tf`
- Modify: `infra/terraform/modules/cleanup-lambda/main.tf`

**Step 1: Add layers variable**

```hcl
variable "layers" {
  description = "List of Lambda Layer ARNs"
  type        = list(string)
  default     = []
}
```

**Step 2: Update Lambda resource**

Add `layers = var.layers` to the aws_lambda_function resource.

**Step 3: Commit**

```bash
git add infra/terraform/modules/cleanup-lambda/
git commit -m "feat: add layers support to cleanup-lambda module"
```

---

## Task 6: Add invoke-cleanup Policy to Terraform

**Files:**
- Modify: `infra/terraform/modules/lambda/variables.tf`
- Modify: `infra/terraform/main.tf`

**Step 1: Add cleanup Lambda ARN to lambda_invoke_arns**

In main.tf, find the lambda module call and update:

```hcl
  lambda_invoke_arns = [
    module.scraper.function_arn,
    "arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:bluemoxon-${var.environment}-cleanup"
  ]
```

**Step 2: Commit**

```bash
git add infra/terraform/main.tf
git commit -m "feat: add cleanup Lambda invoke permission to API role"
```

---

## Task 7: Create Initial Layer Manually (Bootstrap)

Since CI/CD needs an existing layer to reference, create initial layer manually.

**Step 1: Build layer locally**

```bash
cd backend
mkdir -p .tmp/python
pip install -t .tmp/python -r requirements.txt
cd .tmp
zip -r layer.zip python -x "*.pyc" -x "*__pycache__*"
```

**Step 2: Upload to S3**

```bash
AWS_PROFILE=bmx-staging aws s3 cp layer.zip s3://bluemoxon-frontend-staging/lambda/layer.zip
```

**Step 3: Publish layer version**

```bash
AWS_PROFILE=bmx-staging aws lambda publish-layer-version \
  --layer-name bluemoxon-staging-deps \
  --content S3Bucket=bluemoxon-frontend-staging,S3Key=lambda/layer.zip \
  --compatible-runtimes python3.12
```

---

## Task 8: Apply Terraform Changes

**Step 1: Run terraform plan**

```bash
cd infra/terraform
AWS_PROFILE=bmx-staging terraform plan -var-file=envs/staging.tfvars
```

**Step 2: Apply changes**

```bash
AWS_PROFILE=bmx-staging terraform apply -var-file=envs/staging.tfvars
```

---

## Task 9: Update Lambda Functions to Use Layer

**Step 1: Get layer ARN**

```bash
AWS_PROFILE=bmx-staging aws lambda list-layer-versions \
  --layer-name bluemoxon-staging-deps \
  --query 'LayerVersions[0].LayerVersionArn' \
  --output text
```

**Step 2: Update API Lambda**

```bash
AWS_PROFILE=bmx-staging aws lambda update-function-configuration \
  --function-name bluemoxon-staging-api \
  --layers <LAYER_ARN>
```

**Step 3: Create small function package**

```bash
cd backend
rm -rf .tmp/function
mkdir -p .tmp/function
cp -r app .tmp/function/
cp -r lambdas .tmp/function/
cd .tmp/function
zip -r ../function.zip . -x "*.pyc" -x "*__pycache__*"
ls -lh ../function.zip
```

**Step 4: Update cleanup Lambda**

```bash
AWS_PROFILE=bmx-staging aws s3 cp .tmp/function.zip s3://bluemoxon-frontend-staging/lambda/cleanup.zip
AWS_PROFILE=bmx-staging aws lambda update-function-code \
  --function-name bluemoxon-staging-cleanup \
  --s3-bucket bluemoxon-frontend-staging \
  --s3-key lambda/cleanup.zip
AWS_PROFILE=bmx-staging aws lambda update-function-configuration \
  --function-name bluemoxon-staging-cleanup \
  --layers <LAYER_ARN>
```

---

## Task 10: Verify Cleanup Endpoint Works

**Step 1: Test cleanup endpoint**

```bash
bmx-api POST /admin/cleanup '{"action":"all"}'
```

**Expected:** Valid response with cleanup counts, no 500 error.

**Step 2: Check Lambda logs**

```bash
AWS_PROFILE=bmx-staging aws logs tail /aws/lambda/bluemoxon-staging-cleanup --since 2m
```

**Expected:** No import errors, successful execution.

---

## Summary

| Component | Before | After |
|-----------|--------|-------|
| Lambda package | ~50MB monolith | <1MB function code |
| Dependencies | Bundled every deploy | Layer updated on poetry.lock change |
| Deploy time | ~3 min package build | <30 sec for code-only |
| Size limit | Risk of hitting 66MB | Well under limits |
