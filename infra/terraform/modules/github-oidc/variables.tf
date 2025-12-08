variable "cloudfront_distribution_arns" {
  type        = list(string)
  description = "CloudFront distribution ARNs for cache invalidation"
  default     = []
}

variable "frontend_bucket_arns" {
  type        = list(string)
  description = "S3 bucket ARNs for frontend deployment"
  default     = []
}

variable "github_repo" {
  type        = string
  description = "GitHub repository in format 'owner/repo'"
}

variable "images_bucket_arns" {
  type        = list(string)
  description = "S3 bucket ARNs for images access"
  default     = []
}

variable "lambda_function_arns" {
  type        = list(string)
  description = "Lambda function ARN patterns for deployment (supports wildcards)"
}

variable "policy_name" {
  type        = string
  description = "Name of the IAM policy"
  default     = "github-actions-deploy-policy"
}

variable "role_name" {
  type        = string
  description = "Name of the IAM role"
  default     = "github-actions-deploy"
}

variable "tags" {
  type        = map(string)
  description = "Resource tags"
  default     = {}
}
