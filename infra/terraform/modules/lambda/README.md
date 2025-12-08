# Lambda Module

Creates a Lambda function with IAM role, CloudWatch logging, X-Ray tracing, optional VPC configuration, and provisioned concurrency support.

## Usage

```hcl
module "api" {
  source = "./modules/lambda"

  environment      = "production"
  function_name    = "my-app-api"
  handler          = "app.main.handler"
  package_path     = "${path.root}/../../backend/dist/lambda.zip"
  source_code_hash = filebase64sha256("${path.root}/../../backend/dist/lambda.zip")

  memory_size              = 512
  timeout                  = 30
  provisioned_concurrency  = 1

  environment_variables = {
    DATABASE_URL = "postgresql://..."
  }

  tags = {
    Environment = "production"
  }
}
```

## Requirements

| Name | Version |
|------|---------|
| terraform | >= 1.6.0 |
| aws | ~> 5.0 |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| cognito_user_pool_arns | Cognito user pool ARNs for admin operations | `list(string)` | `[]` | no |
| create_security_group | Create a security group for the Lambda | `bool` | `false` | no |
| environment | Environment name (staging, prod) | `string` | n/a | yes |
| environment_variables | Environment variables for the Lambda function | `map(string)` | `{}` | no |
| function_name | Name of the Lambda function | `string` | n/a | yes |
| handler | Lambda function handler | `string` | `"app.main.handler"` | no |
| log_retention_days | CloudWatch log retention in days | `number` | `14` | no |
| memory_size | Memory allocation in MB | `number` | `512` | no |
| package_path | Path to the Lambda deployment package | `string` | n/a | yes |
| provisioned_concurrency | Provisioned concurrency for warm starts (0 = scale to zero) | `number` | `0` | no |
| runtime | Lambda runtime | `string` | `"python3.12"` | no |
| security_group_ids | Security group IDs for Lambda | `list(string)` | `[]` | no |
| source_code_hash | Base64-encoded SHA256 hash of the package file | `string` | n/a | yes |
| subnet_ids | VPC subnet IDs for Lambda | `list(string)` | `[]` | no |
| tags | Resource tags | `map(string)` | `{}` | no |
| timeout | Function timeout in seconds | `number` | `30` | no |

## Outputs

| Name | Description |
|------|-------------|
| alias_arn | ARN of the Lambda alias (if provisioned concurrency is enabled) |
| alias_invoke_arn | Invoke ARN of the Lambda alias (if provisioned concurrency is enabled) |
| function_arn | ARN of the Lambda function |
| function_name | Name of the Lambda function |
| invoke_arn | Invoke ARN for API Gateway integration |
| log_group_name | CloudWatch log group name |
| role_arn | ARN of the Lambda execution role |
| role_name | Name of the Lambda execution role |
