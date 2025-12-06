output "distribution_arn" {
  description = "ARN of the CloudFront distribution"
  value       = aws_cloudfront_distribution.this.arn
}

output "distribution_domain_name" {
  description = "Domain name of the CloudFront distribution"
  value       = aws_cloudfront_distribution.this.domain_name
}

output "distribution_id" {
  description = "ID of the CloudFront distribution"
  value       = aws_cloudfront_distribution.this.id
}

output "oai_arn" {
  description = "ARN of the Origin Access Identity"
  value       = aws_cloudfront_origin_access_identity.this.iam_arn
}

output "oai_path" {
  description = "CloudFront access identity path"
  value       = aws_cloudfront_origin_access_identity.this.cloudfront_access_identity_path
}
