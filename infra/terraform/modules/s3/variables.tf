variable "block_public_access" {
  type        = bool
  description = "Block all public access to the bucket"
  default     = true
}

variable "bucket_name" {
  type        = string
  description = "Name of the S3 bucket"
}

variable "cloudfront_oai_arn" {
  type        = string
  description = "CloudFront Origin Access Identity ARN for bucket policy"
  default     = null
}

variable "cors_allowed_headers" {
  type        = list(string)
  description = "Allowed headers for CORS"
  default     = ["*"]
}

variable "cors_allowed_methods" {
  type        = list(string)
  description = "Allowed methods for CORS"
  default     = ["GET", "HEAD"]
}

variable "cors_allowed_origins" {
  type        = list(string)
  description = "Allowed origins for CORS"
  default     = []
}

variable "cors_expose_headers" {
  type        = list(string)
  description = "Headers to expose in CORS response"
  default     = []
}

variable "cors_max_age_seconds" {
  type        = number
  description = "Max age for CORS preflight cache"
  default     = 3600
}

variable "enable_cloudfront_policy" {
  type        = bool
  description = "Enable CloudFront bucket policy (use this instead of checking oai_arn for count)"
  default     = false
}

variable "enable_versioning" {
  type        = bool
  description = "Enable bucket versioning"
  default     = false
}

variable "enable_website" {
  type        = bool
  description = "Enable static website hosting"
  default     = false
}

variable "secondary_cloudfront_distribution_arns" {
  type        = list(string)
  description = "Additional CloudFront distribution ARNs that need OAC access to this bucket"
  default     = []
}

variable "tags" {
  type        = map(string)
  description = "Resource tags"
  default     = {}
}
