variable "acm_certificate_arn" {
  type        = string
  description = "ACM certificate ARN for HTTPS"
  default     = null
}

variable "cloudfront_function_arn" {
  type        = string
  description = "ARN of CloudFront function to attach to secondary origin (optional)"
  default     = null
}

variable "comment" {
  type        = string
  description = "Comment for the CloudFront distribution"
  default     = ""
}

variable "default_root_object" {
  type        = string
  description = "Default root object"
  default     = "index.html"
}

variable "default_ttl" {
  type        = number
  description = "Default TTL in seconds"
  default     = 86400
}

variable "domain_aliases" {
  type        = list(string)
  description = "Domain aliases for the distribution"
  default     = []
}

variable "max_ttl" {
  type        = number
  description = "Maximum TTL in seconds"
  default     = 31536000
}

variable "oac_description" {
  type        = string
  description = "Description for the Origin Access Control"
  default     = "OAC for S3 bucket access"
}

variable "oac_name" {
  type        = string
  description = "Name for the Origin Access Control (used when origin_access_type = 'oac')"
  default     = null
}

variable "oai_comment" {
  type        = string
  description = "Comment for the Origin Access Identity (used when origin_access_type = 'oai')"
  default     = "OAI for S3 bucket access"
}

variable "origin_access_type" {
  type        = string
  description = "Type of S3 origin access: 'oai' (legacy Origin Access Identity) or 'oac' (modern Origin Access Control)"
  default     = "oai"

  validation {
    condition     = contains(["oai", "oac"], var.origin_access_type)
    error_message = "origin_access_type must be 'oai' or 'oac'"
  }
}

variable "price_class" {
  type        = string
  description = "CloudFront price class"
  default     = "PriceClass_100"
}

variable "s3_bucket_arn" {
  type        = string
  description = "ARN of the S3 bucket (required for OAC bucket policy)"
  default     = null
}

variable "s3_bucket_domain_name" {
  type        = string
  description = "Regional domain name of the S3 bucket"
}

variable "s3_bucket_name" {
  type        = string
  description = "Name of the S3 bucket origin"
}

variable "tags" {
  type        = map(string)
  description = "Resource tags"
  default     = {}
}

# =============================================================================
# Cache and Policy Settings
# =============================================================================

variable "cache_policy_id" {
  type        = string
  description = "Cache policy ID (managed policy). When set, TTL values and forwarded_values are ignored."
  default     = null
}

variable "error_caching_min_ttl" {
  type        = number
  description = "Minimum TTL for caching error responses"
  default     = 300
}

variable "http_version" {
  type        = string
  description = "HTTP version for CloudFront (http1.1, http2, http2and3, http3)"
  default     = "http2"
}

variable "logging_bucket" {
  type        = string
  description = "S3 bucket for access logs (e.g., 'bucket-name.s3.amazonaws.com')"
  default     = null
}

variable "logging_prefix" {
  type        = string
  description = "Prefix for access log files"
  default     = "cloudfront/"
}

variable "response_headers_policy_id" {
  type        = string
  description = "Response headers policy ID (managed policy)"
  default     = null
}

# =============================================================================
# Multi-Origin Support (Optional - for production's combined distribution)
# =============================================================================

variable "secondary_origin_bucket_domain_name" {
  type        = string
  description = "Regional domain name of secondary S3 bucket (optional, for multi-origin distributions)"
  default     = null
}

variable "secondary_origin_bucket_name" {
  type        = string
  description = "Name of secondary S3 bucket origin (optional, for multi-origin distributions)"
  default     = null
}

variable "secondary_origin_oac_id" {
  type        = string
  description = "OAC ID for secondary origin (optional, for multi-origin distributions with OAC)"
  default     = null
}

variable "secondary_origin_path_pattern" {
  type        = string
  description = "Path pattern for secondary origin cache behavior (e.g., '/book-images/*')"
  default     = null
}

variable "secondary_origin_ttl" {
  type        = number
  description = "TTL for secondary origin cache behavior in seconds"
  default     = 604800 # 7 days
}

variable "secondary_origin_oac_name" {
  type        = string
  description = "Name for secondary origin OAC (optional, defaults to bucket-name-oac)"
  default     = null
}

variable "secondary_origin_oac_description" {
  type        = string
  description = "Description for secondary origin OAC"
  default     = "OAC for secondary S3 bucket access"
}

variable "secondary_origin_function_arn" {
  type        = string
  description = "ARN of CloudFront function for secondary origin viewer-request (e.g., path prefix stripping)"
  default     = null
}
