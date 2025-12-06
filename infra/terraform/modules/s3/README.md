# S3 Bucket Module

Creates an S3 bucket with configurable versioning, encryption, public access blocking, CORS, static website hosting, and CloudFront OAI policy.

## Usage

```hcl
module "frontend_bucket" {
  source = "./modules/s3"

  bucket_name              = "my-app-frontend"
  enable_versioning        = false
  block_public_access      = true
  enable_cloudfront_policy = true
  cloudfront_oai_arn       = module.cdn.oai_arn

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
| block_public_access | Block all public access to the bucket | `bool` | `true` | no |
| bucket_name | Name of the S3 bucket | `string` | n/a | yes |
| cloudfront_oai_arn | CloudFront Origin Access Identity ARN for bucket policy | `string` | `null` | no |
| cors_allowed_headers | Allowed headers for CORS | `list(string)` | `["*"]` | no |
| cors_allowed_methods | Allowed methods for CORS | `list(string)` | `["GET", "HEAD"]` | no |
| cors_allowed_origins | Allowed origins for CORS | `list(string)` | `[]` | no |
| cors_expose_headers | Headers to expose in CORS response | `list(string)` | `[]` | no |
| cors_max_age_seconds | Max age for CORS preflight cache | `number` | `3600` | no |
| enable_cloudfront_policy | Enable CloudFront bucket policy | `bool` | `false` | no |
| enable_versioning | Enable bucket versioning | `bool` | `false` | no |
| enable_website | Enable static website hosting | `bool` | `false` | no |
| tags | Resource tags | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
|------|-------------|
| bucket_arn | ARN of the S3 bucket |
| bucket_domain_name | Domain name of the S3 bucket |
| bucket_id | ID of the S3 bucket |
| bucket_name | Name of the S3 bucket |
| bucket_regional_domain_name | Regional domain name of the S3 bucket |
| website_endpoint | Website endpoint (if enabled) |
