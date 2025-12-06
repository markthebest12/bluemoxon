# =============================================================================
# Required Variables
# =============================================================================

variable "bucket_name" {
  description = "Name of the S3 bucket"
  type        = string
}

# =============================================================================
# Optional Variables
# =============================================================================

variable "enable_versioning" {
  description = "Enable bucket versioning"
  type        = bool
  default     = false
}

variable "block_public_access" {
  description = "Block all public access to the bucket"
  type        = bool
  default     = true
}

variable "enable_website" {
  description = "Enable static website hosting"
  type        = bool
  default     = false
}

variable "cloudfront_oai_arn" {
  description = "CloudFront Origin Access Identity ARN for bucket policy"
  type        = string
  default     = null
}

variable "enable_cloudfront_policy" {
  description = "Enable CloudFront bucket policy (use this instead of checking oai_arn for count)"
  type        = bool
  default     = false
}

# =============================================================================
# CORS Configuration
# =============================================================================

variable "cors_allowed_origins" {
  description = "Allowed origins for CORS"
  type        = list(string)
  default     = []
}

variable "cors_allowed_methods" {
  description = "Allowed methods for CORS"
  type        = list(string)
  default     = ["GET", "HEAD"]
}

variable "cors_allowed_headers" {
  description = "Allowed headers for CORS"
  type        = list(string)
  default     = ["*"]
}

variable "cors_expose_headers" {
  description = "Headers to expose in CORS response"
  type        = list(string)
  default     = []
}

variable "cors_max_age_seconds" {
  description = "Max age for CORS preflight cache"
  type        = number
  default     = 3600
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
