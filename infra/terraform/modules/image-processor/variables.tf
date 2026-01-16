variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name (staging/production)"
  type        = string
}

variable "s3_bucket" {
  description = "S3 bucket containing Lambda deployment package"
  type        = string
}

variable "s3_key" {
  description = "S3 key for Lambda deployment package"
  type        = string
}

variable "images_bucket" {
  description = "S3 bucket for book images"
  type        = string
}

variable "images_cdn_domain" {
  description = "CloudFront domain for images CDN"
  type        = string
}

variable "database_secret_arn" {
  description = "ARN of the database credentials secret"
  type        = string
}

variable "memory_size" {
  description = "Lambda memory size in MB"
  type        = number
  default     = 1024
}

variable "timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 300
}

variable "reserved_concurrency" {
  description = "Reserved concurrent executions"
  type        = number
  default     = 2
}

variable "environment_variables" {
  description = "Additional environment variables"
  type        = map(string)
  default     = {}
}
