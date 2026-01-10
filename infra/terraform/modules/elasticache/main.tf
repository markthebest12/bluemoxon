# Security group for ElastiCache
resource "aws_security_group" "redis" {
  name_prefix = "bmx-${var.environment}-redis-"
  vpc_id      = var.vpc_id
  description = "Security group for ElastiCache Redis"

  ingress {
    description     = "Redis from Lambda"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [var.lambda_security_group_id]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "bmx-${var.environment}-redis-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# ElastiCache Serverless (Redis)
resource "aws_elasticache_serverless_cache" "this" {
  engine = "redis"
  name   = "bmx-${var.environment}-cache"

  cache_usage_limits {
    data_storage {
      maximum = 1
      unit    = "GB"
    }
    ecpu_per_second {
      maximum = 1000
    }
  }

  daily_snapshot_time      = "05:00"
  description              = "Dashboard stats cache for ${var.environment}"
  major_engine_version     = "7"
  snapshot_retention_limit = 1
  subnet_ids               = var.subnet_ids
  security_group_ids       = [aws_security_group.redis.id]

  tags = merge(var.tags, {
    Name = "bmx-${var.environment}-cache"
  })
}
