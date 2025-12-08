# Database Sync Lambda Module

Creates a Lambda function for syncing production database to staging.

## Features

- Lambda function with VPC configuration for database access
- IAM role with Secrets Manager and VPC permissions
- CloudWatch log group with configurable retention

## Usage

```hcl
module "db_sync_lambda" {
  source = "./modules/db-sync-lambda"

  function_name      = "bluemoxon-staging-db-sync"
  subnet_ids         = var.private_subnet_ids
  security_group_ids = [aws_security_group.db_sync.id]
  secret_arns        = [aws_secretsmanager_secret.prod_db.arn, aws_secretsmanager_secret.staging_db.arn]

  environment_variables = {
    SOURCE_SECRET_ARN = aws_secretsmanager_secret.prod_db.arn
    TARGET_SECRET_ARN = aws_secretsmanager_secret.staging_db.arn
  }

  tags = var.tags
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| environment_variables | Environment variables for the Lambda | `map(string)` | `{}` | no |
| function_name | Name of the Lambda function | `string` | n/a | yes |
| log_retention_days | CloudWatch log retention in days | `number` | `14` | no |
| memory_size | Memory size in MB | `number` | `512` | no |
| package_path | Path to the Lambda deployment package | `string` | `"db-sync-lambda.zip"` | no |
| runtime | Lambda runtime | `string` | `"python3.12"` | no |
| secret_arns | ARNs of secrets the Lambda needs to access | `list(string)` | n/a | yes |
| security_group_ids | Security group IDs for VPC configuration | `list(string)` | n/a | yes |
| source_code_hash | Base64-encoded SHA256 hash of the package | `string` | `""` | no |
| subnet_ids | Subnet IDs for VPC configuration | `list(string)` | n/a | yes |
| tags | Resource tags | `map(string)` | `{}` | no |
| timeout | Timeout in seconds | `number` | `900` | no |

## Outputs

| Name | Description |
|------|-------------|
| function_arn | Lambda function ARN |
| function_name | Lambda function name |
| invoke_arn | Lambda invoke ARN |
| role_arn | IAM role ARN |
