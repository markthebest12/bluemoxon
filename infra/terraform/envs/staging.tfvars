# =============================================================================
# Staging Environment Configuration
# =============================================================================

environment    = "staging"
aws_account_id = "652617421195"
aws_region     = "us-west-2"

# Domain configuration
domain_name   = "bluemoxon.com"
api_subdomain = "staging-api"
app_subdomain = "staging"

# Lambda - smaller for staging, scales to zero when idle
lambda_memory_size             = 256
lambda_timeout                 = 30
lambda_provisioned_concurrency = 0  # No provisioned concurrency = scale to zero

# Database - minimal for staging
db_instance_class    = "db.t3.micro"
db_allocated_storage = 20

# Feature flags
enable_cloudfront = true
enable_waf        = false
