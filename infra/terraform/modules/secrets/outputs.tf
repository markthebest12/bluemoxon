# =============================================================================
# Outputs
# =============================================================================

output "arn" {
  description = "ARN of the secret"
  value       = aws_secretsmanager_secret.this.arn
}

output "id" {
  description = "ID of the secret"
  value       = aws_secretsmanager_secret.this.id
}

output "name" {
  description = "Name of the secret"
  value       = aws_secretsmanager_secret.this.name
}

output "version_id" {
  description = "Version ID of the current secret version"
  value       = aws_secretsmanager_secret_version.this.version_id
}
