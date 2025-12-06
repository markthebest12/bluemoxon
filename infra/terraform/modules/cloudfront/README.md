# CloudFront Module

Creates a CloudFront distribution with S3 origin, Origin Access Identity, and optional custom domain support.

## Usage

```hcl
module "frontend_cdn" {
  source = "./modules/cloudfront"

  s3_bucket_name        = module.frontend_bucket.bucket_name
  s3_bucket_domain_name = module.frontend_bucket.bucket_regional_domain_name
  domain_aliases        = ["app.example.com"]
  acm_certificate_arn   = aws_acm_certificate.main.arn
  comment               = "Frontend CDN"

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
| acm_certificate_arn | ACM certificate ARN for HTTPS | `string` | `null` | no |
| comment | Comment for the CloudFront distribution | `string` | `""` | no |
| default_root_object | Default root object | `string` | `"index.html"` | no |
| default_ttl | Default TTL in seconds | `number` | `86400` | no |
| domain_aliases | Domain aliases for the distribution | `list(string)` | `[]` | no |
| max_ttl | Maximum TTL in seconds | `number` | `31536000` | no |
| oai_comment | Comment for the Origin Access Identity | `string` | `"OAI for S3 bucket access"` | no |
| price_class | CloudFront price class | `string` | `"PriceClass_100"` | no |
| s3_bucket_domain_name | Regional domain name of the S3 bucket | `string` | n/a | yes |
| s3_bucket_name | Name of the S3 bucket origin | `string` | n/a | yes |
| tags | Resource tags | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
|------|-------------|
| distribution_arn | ARN of the CloudFront distribution |
| distribution_domain_name | Domain name of the CloudFront distribution |
| distribution_id | ID of the CloudFront distribution |
| oai_arn | ARN of the Origin Access Identity |
| oai_path | CloudFront access identity path |
