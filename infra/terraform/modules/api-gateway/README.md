# API Gateway Module

Creates an HTTP API Gateway with Lambda integration, CORS configuration, CloudWatch logging, and optional custom domain.

## Usage

```hcl
module "api_gateway" {
  source = "./modules/api-gateway"

  api_name             = "my-app-api"
  lambda_invoke_arn    = module.lambda.invoke_arn
  lambda_function_name = module.lambda.function_name

  domain_name     = "api.example.com"
  certificate_arn = aws_acm_certificate.main.arn

  cors_allowed_origins = ["https://app.example.com"]

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
| api_name | Name of the API Gateway | `string` | n/a | yes |
| certificate_arn | ACM certificate ARN for custom domain | `string` | `null` | no |
| cors_allow_credentials | Allow credentials in CORS | `bool` | `false` | no |
| cors_allowed_headers | Allowed headers for CORS | `list(string)` | `["*"]` | no |
| cors_allowed_methods | Allowed methods for CORS | `list(string)` | `["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]` | no |
| cors_allowed_origins | Allowed origins for CORS | `list(string)` | `["*"]` | no |
| cors_expose_headers | Headers to expose in CORS response | `list(string)` | `["x-app-version", "x-environment"]` | no |
| cors_max_age | Max age for CORS preflight cache | `number` | `3600` | no |
| domain_name | Custom domain name for the API | `string` | `null` | no |
| lambda_function_name | Lambda function name for permission | `string` | n/a | yes |
| lambda_invoke_arn | Lambda function invoke ARN | `string` | n/a | yes |
| log_retention_days | CloudWatch log retention in days | `number` | `14` | no |
| tags | Resource tags | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
|------|-------------|
| api_endpoint | Default endpoint URL of the API |
| api_id | ID of the API Gateway |
| custom_domain_name | Custom domain name (if configured) |
| custom_domain_target | Target domain for DNS CNAME record |
| execution_arn | Execution ARN for Lambda permissions |
| log_group_name | CloudWatch log group name |
