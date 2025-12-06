output "client_id" {
  description = "ID of the user pool client"
  value       = aws_cognito_user_pool_client.this.id
}

output "domain" {
  description = "Cognito domain (if configured)"
  value       = try(aws_cognito_user_pool_domain.this[0].domain, null)
}

output "user_pool_arn" {
  description = "ARN of the Cognito user pool"
  value       = aws_cognito_user_pool.this.arn
}

output "user_pool_endpoint" {
  description = "Endpoint of the Cognito user pool"
  value       = aws_cognito_user_pool.this.endpoint
}

output "user_pool_id" {
  description = "ID of the Cognito user pool"
  value       = aws_cognito_user_pool.this.id
}
