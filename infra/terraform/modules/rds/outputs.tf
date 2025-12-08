output "address" {
  description = "RDS instance address (hostname)"
  value       = aws_db_instance.this.address
}

output "arn" {
  description = "RDS instance ARN"
  value       = aws_db_instance.this.arn
}

output "connection_url" {
  description = "PostgreSQL connection URL (without password)"
  value       = "postgresql://${aws_db_instance.this.username}@${aws_db_instance.this.endpoint}/${aws_db_instance.this.db_name}"
}

output "database_name" {
  description = "Name of the database"
  value       = aws_db_instance.this.db_name
}

output "endpoint" {
  description = "RDS instance endpoint (host:port)"
  value       = aws_db_instance.this.endpoint
}

output "id" {
  description = "RDS instance ID"
  value       = aws_db_instance.this.id
}

output "port" {
  description = "RDS instance port"
  value       = aws_db_instance.this.port
}

output "security_group_id" {
  description = "Security group ID for the RDS instance"
  value       = aws_security_group.this.id
}

output "subnet_group_name" {
  description = "DB subnet group name"
  value       = aws_db_subnet_group.this.name
}

output "username" {
  description = "Master username"
  value       = aws_db_instance.this.username
  sensitive   = true
}
