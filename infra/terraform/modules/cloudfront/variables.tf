variable "acm_certificate_arn" {
  type        = string
  description = "ACM certificate ARN for HTTPS"
  default     = null
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

variable "s3_bucket_arn" {
  type        = string
  description = "ARN of the S3 bucket (required for OAC bucket policy)"
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

variable "oai_comment" {
  type        = string
  description = "Comment for the Origin Access Identity (used when origin_access_type = 'oai')"
  default     = "OAI for S3 bucket access"
}

variable "oac_name" {
  type        = string
  description = "Name for the Origin Access Control (used when origin_access_type = 'oac')"
  default     = null
}

variable "oac_description" {
  type        = string
  description = "Description for the Origin Access Control"
  default     = "OAC for S3 bucket access"
}

variable "price_class" {
  type        = string
  description = "CloudFront price class"
  default     = "PriceClass_100"
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
