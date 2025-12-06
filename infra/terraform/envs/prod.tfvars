# =============================================================================
# Production Environment Configuration
# =============================================================================

environment    = "prod"
aws_account_id = "266672885920"
aws_region     = "us-west-2"

# Domain configuration
domain_name   = "bluemoxon.com"
api_subdomain = "api"
app_subdomain = "app"

# Lambda - production sizing
lambda_memory_size = 512
lambda_timeout     = 30

# Database - production sizing
db_instance_class    = "db.t3.small"
db_allocated_storage = 50

# Feature flags
enable_cloudfront = true
enable_waf        = true
