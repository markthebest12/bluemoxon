variable "acm_certificate_arn" {
  type        = string
  description = "ACM certificate ARN for HTTPS"
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
  description = "Comment for the Origin Access Identity"
  default     = "OAI for S3 bucket access"
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
