# =============================================================================
# Landing Site Module Variables
# =============================================================================

variable "acm_certificate_arn" {
  type        = string
  description = "ARN of ACM certificate for custom domain (must be in us-east-1 for CloudFront)"
  default     = null
}

variable "bucket_name" {
  type        = string
  description = "Name of the S3 bucket for the landing site"
}

variable "cache_policy_id" {
  type        = string
  description = "CloudFront cache policy ID (default: CachingOptimized)"
  default     = "658327ea-f89d-4fab-a63d-7e88639e58f6" # CachingOptimized managed policy
}

variable "comment" {
  type        = string
  description = "Comment for the CloudFront distribution"
  default     = ""
}

variable "default_root_object" {
  type        = string
  description = "Default root object for CloudFront"
  default     = "index.html"
}

variable "domain_aliases" {
  type        = list(string)
  description = "List of domain aliases for the CloudFront distribution"
  default     = []
}

variable "enable_versioning" {
  type        = bool
  description = "Enable S3 bucket versioning"
  default     = false
}

variable "oac_description" {
  type        = string
  description = "Description for the Origin Access Control"
  default     = ""
}

variable "oac_name" {
  type        = string
  description = "Name for the Origin Access Control"
}

variable "origin_id" {
  type        = string
  description = "Origin ID for CloudFront (typically bucket-name-s3)"
}

variable "price_class" {
  type        = string
  description = "CloudFront price class"
  default     = "PriceClass_100" # US, Canada, Europe only
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to all resources"
  default     = {}
}
