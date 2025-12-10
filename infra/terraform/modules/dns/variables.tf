# =============================================================================
# DNS Module Variables
# =============================================================================

variable "api_domain_name" {
  type        = string
  description = "API Gateway custom domain name for api.{domain}"
  default     = null
}

variable "api_domain_zone_id" {
  type        = string
  description = "API Gateway custom domain Route53 hosted zone ID"
  default     = null
}

variable "app_cloudfront_domain_name" {
  type        = string
  description = "CloudFront distribution domain name for app.{domain}"
  default     = null
}

variable "app_cloudfront_zone_id" {
  type        = string
  description = "CloudFront distribution hosted zone ID for app.{domain}"
  default     = "Z2FDTNDATAQYW2" # CloudFront's global zone ID
}

variable "domain_name" {
  type        = string
  description = "Base domain name (e.g., bluemoxon.com)"
}

variable "landing_cloudfront_domain_name" {
  type        = string
  description = "CloudFront distribution domain name for landing site"
  default     = null
}

variable "landing_cloudfront_zone_id" {
  type        = string
  description = "CloudFront distribution hosted zone ID for landing site"
  default     = "Z2FDTNDATAQYW2" # CloudFront's global zone ID
}

variable "staging_api_domain_name" {
  type        = string
  description = "API Gateway custom domain name for staging.api.{domain}"
  default     = null
}

variable "staging_api_domain_zone_id" {
  type        = string
  description = "API Gateway custom domain Route53 hosted zone ID for staging"
  default     = null
}

variable "staging_app_cloudfront_domain_name" {
  type        = string
  description = "CloudFront distribution domain name for staging.app.{domain}"
  default     = null
}

variable "staging_app_cloudfront_zone_id" {
  type        = string
  description = "CloudFront distribution hosted zone ID for staging.app.{domain}"
  default     = "Z2FDTNDATAQYW2" # CloudFront's global zone ID
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to all resources"
  default     = {}
}

variable "zone_comment" {
  type        = string
  description = "Comment for the hosted zone"
  default     = ""
}
