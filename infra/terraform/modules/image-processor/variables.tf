variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name (staging/production)"
  type        = string
}

variable "image_uri" {
  description = "ECR image URI for Lambda container"
  type        = string
  default     = ""
}

variable "ecr_repository_url" {
  description = "ECR repository URL (used as fallback if image_uri is empty)"
  type        = string
}

variable "image_tag" {
  description = "Image tag to use when building image_uri from ecr_repository_url (default: v2 for bootstrap)"
  type        = string
  default     = "v2"
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
  description = "Lambda memory size in MB (10240 required for rembg/u2net which needs ~6.2GB)"
  type        = number
  default     = 10240
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

variable "vpc_subnet_ids" {
  description = "VPC subnet IDs for Lambda"
  type        = list(string)
  default     = []
}

variable "vpc_security_group_ids" {
  description = "VPC security group IDs for Lambda"
  type        = list(string)
  default     = []
}

variable "alarm_sns_topic_arn" {
  description = "SNS topic ARN for DLQ alarm notifications"
  type        = string
  default     = ""
}

variable "api_lambda_role_name" {
  description = "IAM role name of the API Lambda (for SQS send permissions)"
  type        = string
  default     = null
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}
