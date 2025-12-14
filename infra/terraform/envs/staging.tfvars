# =============================================================================
# Staging Environment Configuration
# =============================================================================

environment    = "staging"
aws_account_id = "652617421195"
aws_region     = "us-west-2"

# Domain configuration
domain_name   = "bluemoxon.com"
api_subdomain = "staging.api"
app_subdomain = "staging.app"

# Custom domain ACM certificates (created manually, to be imported)
# CloudFront requires us-east-1 certificate
frontend_acm_cert_arn = "arn:aws:acm:us-east-1:652617421195:certificate/cc72c0b6-da3d-4ffa-8a9d-faffeb52283f"
# API Gateway uses regional certificate (us-west-2)
api_acm_cert_arn = "arn:aws:acm:us-west-2:652617421195:certificate/2de326a8-d05e-4a54-8115-acb4e8eacc85"

# Lambda - matches production for consistent behavior
lambda_memory_size             = 512
lambda_timeout                 = 600
lambda_provisioned_concurrency = 0 # No provisioned concurrency = scale to zero

# Database - minimal for staging
enable_database      = true
db_instance_class    = "db.t3.micro"
db_allocated_storage = 20
# Note: db_password should be passed via TF_VAR_db_password or -var flag, not stored in file

# Feature flags
enable_cloudfront = true
enable_waf        = false
# GitHub OIDC disabled - exists in AWS but cannot be imported with current IAM permissions
# Re-enable after importing with admin credentials using:
#   terraform import 'module.github_oidc[0].aws_iam_openid_connect_provider.github' 'arn:aws:iam::652617421195:oidc-provider/token.actions.githubusercontent.com'
#   terraform import 'module.github_oidc[0].aws_iam_role.github_actions' 'github-actions-deploy'
enable_github_oidc = false

# Cognito MFA - OPTIONAL with TOTP enabled (matches prod)
cognito_mfa_configuration = "OPTIONAL"
cognito_mfa_totp_enabled  = true

# Database sync - production secret ARN for cross-account sync
prod_database_secret_arn = "arn:aws:secretsmanager:us-west-2:266672885920:secret:bluemoxon/db-credentials-Firmtl"

# VPC Networking - NAT Gateway for Lambda outbound access (Cognito API)
enable_nat_gateway = true
public_subnet_id   = "subnet-0c5f84e98ba25334d"
private_subnet_ids = [
  "subnet-0ceb0276fa36428f2",
  "subnet-09eeb023cb49a83d5",
  "subnet-0bfb299044084bad3"
]
# Cognito VPC endpoint only supports us-west-2a/b/c (not 2d)
cognito_endpoint_subnet_ids = [
  "subnet-0ceb0276fa36428f2",
  "subnet-09eeb023cb49a83d5"
]
