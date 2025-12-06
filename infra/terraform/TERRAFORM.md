# BlueMoxon Terraform Infrastructure

## Overview

This directory contains Terraform configuration for deploying BlueMoxon infrastructure to AWS. The configuration is environment-agnostic - use tfvars files to switch between staging and production.

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
│   ├── lambda/           # Lambda function module
│   ├── api-gateway/      # API Gateway HTTP API module
│   ├── s3/               # S3 bucket module
│   ├── cloudfront/       # CloudFront distribution module
│   ├── rds/              # RDS PostgreSQL module
│   └── cognito/          # Cognito User Pool module
├── .tflint.hcl           # TFLint configuration
├── .gitignore            # Git ignore patterns
└── TERRAFORM.md          # This file
```

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

---

## AWS Accounts

| Environment | Account ID | Profile |
|-------------|------------|---------|
| Production | 266672885920 | `prod` |
| Staging | 652617421195 | `staging` |

Switch profiles: `aws-staging` or `aws-prod`

## State Management

State is stored in S3 with DynamoDB locking:

- Bucket: `bluemoxon-terraform-state`
- Lock Table: `bluemoxon-terraform-locks`
- Key Pattern: `bluemoxon/{environment}/terraform.tfstate`
