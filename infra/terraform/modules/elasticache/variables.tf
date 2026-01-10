variable "environment" {
  type        = string
  description = "Environment name (staging, prod)"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID for ElastiCache"
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnet IDs for ElastiCache (private subnets)"
}

variable "lambda_security_group_id" {
  type        = string
  description = "Lambda security group ID (for ingress rules)"
}

variable "tags" {
  type        = map(string)
  description = "Resource tags"
  default     = {}
}
