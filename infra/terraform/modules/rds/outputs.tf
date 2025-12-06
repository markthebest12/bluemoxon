output "address" {
  description = "RDS instance address (hostname)"
  value       = aws_db_instance.this.address
}

output "arn" {
  description = "RDS instance ARN"
  value       = aws_db_instance.this.arn
}

output "database_name" {
  description = "Name of the database"
  value       = aws_db_instance.this.db_name
}

output "endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.this.endpoint
}

output "instance_id" {
  description = "RDS instance ID"
  value       = aws_db_instance.this.id
}

output "port" {
  description = "RDS instance port"
  value       = aws_db_instance.this.port
}

output "security_group_id" {
  description = "Security group ID for the RDS instance"
  value       = aws_security_group.rds.id
}
