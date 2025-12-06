# =============================================================================
# Input Variables
# =============================================================================

# -----------------------------------------------------------------------------
# Required Variables
# -----------------------------------------------------------------------------

variable "allowed_security_group_id" {
  type        = string
  description = "Security group ID allowed to access the database"
}

variable "database_name" {
  type        = string
  description = "Name of the database to create"
}

variable "identifier" {
  type        = string
  description = "RDS instance identifier"
}

variable "master_password" {
  type        = string
  description = "Master password for the database"
  sensitive   = true
}

variable "master_username" {
  type        = string
  description = "Master username for the database"
  sensitive   = true
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnet IDs for the DB subnet group"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID for the security group"
}

# -----------------------------------------------------------------------------
# Optional Variables
# -----------------------------------------------------------------------------

variable "allocated_storage" {
  type        = number
  description = "Allocated storage in GB"
  default     = 20
}

variable "backup_retention_period" {
  type        = number
  description = "Backup retention period in days (0 disables backups)"
  default     = 7
}

variable "backup_window" {
  type        = string
  description = "Preferred backup window (UTC)"
  default     = "03:00-04:00"
}

variable "deletion_protection" {
  type        = bool
  description = "Enable deletion protection"
  default     = true
}

variable "enabled_cloudwatch_logs_exports" {
  type        = list(string)
  description = "List of log types to export to CloudWatch"
  default     = ["postgresql", "upgrade"]
}

variable "engine_version" {
  type        = string
  description = "PostgreSQL engine version"
  default     = "16.3"
}

variable "instance_class" {
  type        = string
  description = "RDS instance class"
  default     = "db.t3.micro"
}

variable "maintenance_window" {
  type        = string
  description = "Preferred maintenance window (UTC)"
  default     = "sun:04:00-sun:05:00"
}

variable "max_allocated_storage" {
  type        = number
  description = "Maximum allocated storage for autoscaling (0 disables autoscaling)"
  default     = 100
}

variable "monitoring_interval" {
  type        = number
  description = "Enhanced monitoring interval in seconds (0 disables)"
  default     = 0
}

variable "parameter_group_name" {
  type        = string
  description = "DB parameter group name"
  default     = null
}

variable "performance_insights_enabled" {
  type        = bool
  description = "Enable Performance Insights"
  default     = false
}

variable "publicly_accessible" {
  type        = bool
  description = "Whether the instance is publicly accessible"
  default     = false
}

variable "skip_final_snapshot" {
  type        = bool
  description = "Skip final snapshot on deletion"
  default     = false
}

variable "tags" {
  type        = map(string)
  description = "Resource tags"
  default     = {}
}
