# BlueMoxon Terraform Infrastructure

## Overview

This directory contains Terraform configuration for deploying BlueMoxon infrastructure to AWS. The configuration is environment-agnostic - use tfvars files to switch between staging and production.

## Environment Comparison

### AWS Accounts

| Environment | Account ID | Purpose | Profile |
|-------------|------------|---------|---------|
| **Production** | `266672885920` | Live user traffic | `prod` |
| **Staging** | `652617421195` | Testing & validation | `staging` |

### Resource Differences

| Resource | Production | Staging | Notes |
|----------|------------|---------|-------|
| **Lambda Memory** | 512 MB | 256 MB | Staging uses less memory |
| **Lambda Provisioned Concurrency** | 1 | 0 | Prod keeps 1 warm; staging scales to zero |
| **RDS Instance** | db.t3.small | db.t3.micro | Staging uses smallest instance |
| **RDS Storage** | 50 GB | 20 GB | Staging has minimal storage |
| **WAF** | Enabled | Disabled | WAF costs ~$5/mo, not needed for staging |
| **CloudFront** | Enabled | Enabled | Both use CDN |

### Domain Configuration

| Environment | API URL | App URL |
|-------------|---------|---------|
| **Production** | `api.bluemoxon.com` | `app.bluemoxon.com` |
| **Staging** | `staging-api.bluemoxon.com` | `staging.bluemoxon.com` |

### Cost Comparison (Estimated Monthly)

| Resource | Production | Staging | Savings |
|----------|------------|---------|---------|
| Lambda | ~$0 (pay per use) | ~$0 (pay per use) | - |
| Lambda Provisioned Concurrency | ~$10/mo | $0 | $10 |
| RDS | ~$25/mo | ~$13/mo | $12 |
| CloudFront | ~$5/mo | ~$1/mo | $4 |
| WAF | ~$5/mo | $0 | $5 |
| S3 | ~$1/mo | ~$0.10/mo | $0.90 |
| **Total** | **~$46/mo** | **~$14/mo** | **~$32** |

### Scaling Behavior

| Environment | Idle Behavior | Cold Start | Cost Impact |
|-------------|---------------|------------|-------------|
| **Production** | 1 Lambda always warm | Eliminated for most requests | Higher base cost |
| **Staging** | Lambda scales to zero | ~500ms cold start | Minimal cost when unused |

---

## Directory Structure

```
terraform/
├── terraform.tf          # Required versions and providers
├── providers.tf          # Provider configuration with default tags
├── backend.tf            # S3 backend configuration
├── main.tf               # Root module - orchestrates all resources
├── variables.tf          # Input variables (alphabetically ordered)
├── outputs.tf            # Output values (alphabetically ordered)
├── locals.tf             # Local values and computed expressions
├── envs/
│   ├── staging.tfvars    # Staging environment values
│   └── prod.tfvars       # Production environment values
├── modules/
│   ├── lambda/           # Lambda function with provisioned concurrency
│   ├── api-gateway/      # API Gateway HTTP API
│   ├── s3/               # S3 buckets (frontend, images)
│   ├── cloudfront/       # CloudFront distributions
│   ├── rds/              # RDS PostgreSQL
│   └── cognito/          # Cognito User Pool (shared)
├── .tflint.hcl           # TFLint configuration
├── .gitignore            # Git ignore patterns
└── TERRAFORM.md          # This file
```

---

## Usage

### Prerequisites

```bash
# Install Terraform
brew install terraform

# Install TFLint
brew install tflint

# Initialize TFLint plugins
cd infra/terraform
tflint --init
```

### Deploy to Staging

```bash
cd infra/terraform

# Initialize with staging backend
terraform init -backend-config="key=bluemoxon/staging/terraform.tfstate"

# Plan changes
terraform plan -var-file=envs/staging.tfvars

# Apply changes
terraform apply -var-file=envs/staging.tfvars
```

### Deploy to Production

```bash
cd infra/terraform

# Initialize with production backend
terraform init -backend-config="key=bluemoxon/prod/terraform.tfstate" -reconfigure

# Plan changes
terraform plan -var-file=envs/prod.tfvars

# Apply changes
terraform apply -var-file=envs/prod.tfvars
```

### Validate and Lint

```bash
# Format check
terraform fmt -check -recursive

# Validate configuration
terraform validate

# Run TFLint
tflint --init
tflint
```

---

## Module Reference

### Lambda Module

Creates a Lambda function with optional provisioned concurrency.

```hcl
module "api" {
  source = "./modules/lambda"

  environment      = var.environment
  function_name    = "${local.name_prefix}-api"
  handler          = "app.main.handler"
  runtime          = var.lambda_runtime
  memory_size      = var.lambda_memory_size
  timeout          = var.lambda_timeout
  package_path     = var.lambda_package_path
  source_code_hash = var.lambda_source_code_hash

  # Provisioned concurrency: 0 = scale to zero, >0 = keep warm
  provisioned_concurrency = var.lambda_provisioned_concurrency

  environment_variables = {
    DATABASE_URL = "..."
  }

  tags = local.common_tags
}
```

**Key Variables:**

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `provisioned_concurrency` | number | 0 | Warm instances (0 = scale to zero) |
| `memory_size` | number | 512 | Memory in MB |
| `timeout` | number | 30 | Timeout in seconds |

### RDS Module

Creates a PostgreSQL RDS instance with CloudWatch logging.

```hcl
module "database" {
  source = "./modules/rds"

  identifier     = "${local.name_prefix}-db"
  vpc_id         = module.vpc.vpc_id
  subnet_ids     = module.vpc.private_subnet_ids
  database_name  = var.db_name
  instance_class = var.db_instance_class

  master_username = var.db_username
  master_password = var.db_password

  tags = local.common_tags
}
```

### S3 Module

Creates S3 buckets with optional CloudFront OAI access.

```hcl
module "frontend_bucket" {
  source = "./modules/s3"

  bucket_name         = "${local.name_prefix}-frontend"
  enable_versioning   = true
  block_public_access = true
  cloudfront_oai_arn  = module.cloudfront.oai_arn

  tags = local.common_tags
}
```

### CloudFront Module

Creates CloudFront distributions for frontend and images.

```hcl
module "cloudfront" {
  source = "./modules/cloudfront"

  environment        = var.environment
  domain_name        = var.domain_name
  s3_bucket_id       = module.frontend_bucket.bucket_id
  s3_bucket_domain   = module.frontend_bucket.bucket_regional_domain_name
  acm_certificate_arn = var.acm_certificate_arn

  tags = local.common_tags
}
```

---

## State Management

State is stored in S3 with DynamoDB locking:

| Component | Value |
|-----------|-------|
| Bucket | `bluemoxon-terraform-state` |
| Lock Table | `bluemoxon-terraform-locks` |
| Key Pattern | `bluemoxon/{environment}/terraform.tfstate` |

Each environment has isolated state - changes to staging never affect production state.

---

## Shared Resources

### Cognito (Authentication)

Staging uses the **production Cognito User Pool** for authentication. This allows:
- Same users work in both environments
- No duplicate user management
- Cross-account JWT validation (stateless)

```hcl
# Both environments reference prod Cognito
cognito_user_pool_id = "us-west-2_PvdIpXVKF"
cognito_client_id    = "3ndaok3psd2ncqfjrdb57825he"
```

### ACM Certificate

Both environments share the wildcard certificate `*.bluemoxon.com`:

```hcl
acm_certificate_arn = "arn:aws:acm:us-east-1:266672885920:certificate/..."
```

---

## CI/CD Workflows

| Workflow | Trigger | Target | File |
|----------|---------|--------|------|
| Terraform CI | PR to main (infra/** changes) | Validate & plan | `.github/workflows/terraform.yml` |
| Deploy Prod | Push to main | Production | `.github/workflows/deploy.yml` |
| Deploy Staging | Push to staging | Staging | `.github/workflows/deploy-staging.yml` |

### Terraform CI Steps

1. Format check (`terraform fmt -check`)
2. Validate (`terraform validate`)
3. TFLint
4. Checkov security scan
5. Plan (for visibility, not applied)

---

## Claude Instructions

**IMPORTANT**: When making changes to Terraform code, follow these guidelines:

### Style Guide (HashiCorp Standards)

1. **File Organization**
   - `terraform.tf` - Required version and providers block
   - `providers.tf` - Provider configuration
   - `backend.tf` - Backend configuration
   - `main.tf` - Resource and data source blocks
   - `variables.tf` - Variable blocks (alphabetically ordered)
   - `outputs.tf` - Output blocks (alphabetically ordered)
   - `locals.tf` - Local values

2. **Naming Conventions**
   - Use `snake_case` for all identifiers (resources, variables, outputs)
   - Resource names should be descriptive nouns, NOT include the resource type
   - Good: `resource "aws_instance" "web_api"`
   - Bad: `resource "aws_instance" "web_api_instance"`

3. **Formatting**
   - Indent with 2 spaces
   - Align `=` signs in argument blocks
   - Place meta-arguments first (`count`, `for_each`)
   - Place `lifecycle` and `depends_on` last
   - Run `terraform fmt` before committing

4. **Variables**
   - Always include `description`
   - Always include `type`
   - Use `sensitive = true` for secrets
   - Group variables with comment headers
   - Order: type, description, default, sensitive, validation

5. **Modules**
   - Each module has: `main.tf`, `variables.tf`, `outputs.tf`
   - Modules should do ONE thing well
   - Maximize outputs even if not immediately needed
   - Keep nesting to 2 levels max

### Environment Switching

The configuration uses tfvars files for environment-specific values:

- **DO NOT** hardcode environment-specific values in `.tf` files
- **DO** use variables for anything that differs between environments
- **DO** use `locals.tf` for computed values based on environment

Example:
```hcl
# Good - in variables.tf
variable "environment" {
  type = string
}

# Good - in locals.tf
locals {
  name_prefix = "${var.app_name}-${var.environment}"
}

# Bad - hardcoded
resource "aws_s3_bucket" "frontend" {
  bucket = "bluemoxon-frontend-staging"  # DON'T DO THIS
}

# Good - parameterized
resource "aws_s3_bucket" "frontend" {
  bucket = "${local.name_prefix}-frontend"
}
```

### Adding New Resources

1. Determine if resource belongs in a module or root
2. If module: create/update in `modules/<name>/`
3. If root: add to `main.tf`
4. Add any new variables to `variables.tf` (alphabetically)
5. Add any new outputs to `outputs.tf` (alphabetically)
6. Update both `staging.tfvars` and `prod.tfvars` if needed
7. Run `terraform fmt -recursive`
8. Run `tflint`
9. Run `terraform validate`

### New Module Checklist

When creating a new Terraform module:

#### Required Files
- [ ] `main.tf` - Resources and data sources
- [ ] `variables.tf` - Input variables (alphabetically ordered)
- [ ] `outputs.tf` - Output values (alphabetically ordered)
- [ ] `versions.tf` - Provider version constraints (see template below)

#### versions.tf Template
```hcl
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
```

#### Variable Requirements
Every variable MUST include:
- `type` - Explicit type constraint
- `description` - Human-readable description
- `default` - For optional variables only

#### Module Design Principles
1. **Single Purpose**: Each module does ONE thing well
2. **80% Use Case**: Design for common cases, avoid edge case complexity
3. **Expose Common Args**: Only expose frequently-modified arguments
4. **Output Everything**: Export all useful values even if not immediately needed
5. **Sensible Defaults**: Required inputs have no default; optional inputs have good defaults

### Pre-Commit Checklist

Before committing Terraform changes:

```bash
# Format
terraform fmt -recursive

# Validate
terraform validate

# Lint
tflint

# Plan (to verify no errors)
terraform plan -var-file=envs/staging.tfvars
```

### Sensitive Data

- **NEVER** commit secrets to tfvars files
- Use AWS SSM Parameter Store or Secrets Manager
- Reference secrets via `data` sources:

```hcl
data "aws_ssm_parameter" "db_password" {
  name = "/${var.environment}/bluemoxon/db_password"
}

# Use: data.aws_ssm_parameter.db_password.value
```
