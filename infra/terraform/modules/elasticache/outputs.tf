output "redis_endpoint" {
  description = "Redis endpoint URL"
  value       = "rediss://${aws_elasticache_serverless_cache.this.endpoint[0].address}:${aws_elasticache_serverless_cache.this.endpoint[0].port}"
}

output "security_group_id" {
  description = "ElastiCache security group ID"
  value       = aws_security_group.redis.id
}

output "cache_name" {
  description = "ElastiCache serverless cache name"
  value       = aws_elasticache_serverless_cache.this.name
}
