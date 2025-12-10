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

# Lambda - production sizing with warm starts
lambda_memory_size             = 512
lambda_timeout                 = 30
lambda_provisioned_concurrency = 1 # Keep 1 instance warm to avoid cold starts

# Database - production sizing
db_instance_class    = "db.t3.small"
db_allocated_storage = 50

# Feature flags
# Production uses existing infrastructure that was set up before Terraform.
# Several resources have architectural differences that make them incompatible
# with the Terraform modules. They are managed externally.
#
# CloudFront: Uses OAC (Origin Access Control), module uses OAI
# Lambda: Different IAM role structure, VPC config, env var names
# Database: Lambda VPC config depends on database module
# VPC: Lambda references VPC resources
enable_cloudfront         = false
enable_lambda             = false
enable_database           = false
enable_nat_gateway        = false
enable_waf                = true
skip_s3_cloudfront_policy = true # Prod uses OAC (not OAI) - bucket policy managed externally

# ACM Certificates
api_acm_cert_arn      = "arn:aws:acm:us-west-2:266672885920:certificate/85f33a7f-bd9e-4e60-befe-95cffea5cf9a"
frontend_acm_cert_arn = "arn:aws:acm:us-east-1:266672885920:certificate/92395aeb-a01e-4a48-b4bd-0a9f1c04e861"

# External Lambda configuration (managed outside Terraform)
lambda_function_name_external = "bluemoxon-api"
lambda_invoke_arn_external    = "arn:aws:apigateway:us-west-2:lambda:path/2015-03-31/functions/arn:aws:lambda:us-west-2:266672885920:function:bluemoxon-api/invocations"

# Cognito settings - preserve existing prod configuration
cognito_mfa_configuration        = "OPTIONAL"
cognito_mfa_totp_enabled         = true
cognito_password_require_symbols = false
cognito_client_name_override     = "bluemoxon-web"
cognito_callback_urls_override = [
  "http://localhost:5173/callback",
  "https://bluemoxon.com/callback",
  "https://staging.app.bluemoxon.com/callback",
  "https://www.bluemoxon.com/callback"
]
cognito_logout_urls_override = [
  "http://localhost:5173",
  "https://bluemoxon.com",
  "https://staging.app.bluemoxon.com",
  "https://www.bluemoxon.com"
]
cognito_allow_admin_create_user_only = true
cognito_invite_email_subject         = "Welcome to BlueMoxon - Your Account is Ready"
cognito_invite_email_message         = <<-EOT
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); padding: 30px; border-radius: 12px 12px 0 0; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 28px;">BlueMoxon</h1>
        <p style="color: #dbeafe; margin: 10px 0 0 0; font-size: 14px;">Book Collection Management</p>
    </div>
    <div style="background: #f8fafc; padding: 30px; border: 1px solid #e2e8f0; border-top: none; border-radius: 0 0 12px 12px;">
        <h2 style="color: #1e293b; margin: 0 0 20px 0; font-size: 20px;">Welcome to BlueMoxon!</h2>
        <p style="color: #475569; line-height: 1.6; margin: 0 0 20px 0;">
            You've been invited to join BlueMoxon. Use the credentials below to sign in:
        </p>
        <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin: 20px 0;">
            <p style="margin: 0 0 10px 0; color: #64748b; font-size: 14px;"><strong>Username:</strong></p>
            <p style="margin: 0 0 20px 0; color: #1e293b; font-size: 16px; font-family: monospace; background: #f1f5f9; padding: 10px; border-radius: 4px;">{username}</p>
            <p style="margin: 0 0 10px 0; color: #64748b; font-size: 14px;"><strong>Temporary Password:</strong></p>
            <p style="margin: 0; color: #1e293b; font-size: 16px; font-family: monospace; background: #f1f5f9; padding: 10px; border-radius: 4px;">{####}</p>
        </div>
        <p style="color: #475569; line-height: 1.6; margin: 0 0 20px 0;">
            You'll be asked to create a new password when you first sign in.
        </p>
        <div style="text-align: center; margin-top: 30px;">
            <a href="https://app.bluemoxon.com" style="background: #2563eb; color: white; padding: 12px 30px; border-radius: 6px; text-decoration: none; font-weight: bold; display: inline-block;">Sign In to BlueMoxon</a>
        </div>
        <p style="color: #94a3b8; font-size: 12px; margin: 30px 0 0 0; text-align: center;">
            This invitation expires in 7 days. If you didn't expect this invitation, please ignore this email.
        </p>
    </div>
</div>
EOT

# =============================================================================
# Legacy Resource Name Overrides
# =============================================================================
# Production uses original naming convention without environment suffix.
# These overrides ensure Terraform manages existing resources without renaming.

frontend_bucket_name_override   = "bluemoxon-frontend"
images_bucket_name_override     = "bluemoxon-images"
lambda_function_name_override   = "bluemoxon-api"
api_gateway_name_override       = "bluemoxon-api"
cognito_user_pool_name_override = "bluemoxon-users"
cognito_domain_override         = "bluemoxon"

# Logs bucket for CloudFront access logs (prod only)
logs_bucket_name = "bluemoxon-logs"

# Landing site (bluemoxon.com marketing site)
enable_landing_site  = true
landing_bucket_name  = "bluemoxon-landing"
landing_acm_cert_arn = "arn:aws:acm:us-east-1:266672885920:certificate/92395aeb-a01e-4a48-b4bd-0a9f1c04e861"

# GitHub OIDC - Override bucket ARNs for legacy naming convention
# Prod uses bluemoxon-frontend/bluemoxon-images instead of bluemoxon-prod-frontend
github_oidc_frontend_bucket_arns = ["arn:aws:s3:::bluemoxon-frontend"]
github_oidc_images_bucket_arns   = ["arn:aws:s3:::bluemoxon-images"]
github_oidc_cloudfront_distribution_arns = [
  "arn:aws:cloudfront::266672885920:distribution/E16BJX90QWQNQO"
]

# =============================================================================
# Route53 DNS (prod only - manages DNS for both prod and staging)
# =============================================================================
# The prod Route53 hosted zone contains records pointing to resources in both
# prod and staging AWS accounts.

enable_dns = true

# Landing site CloudFront (bluemoxon.com, www.bluemoxon.com)
landing_cloudfront_domain_name = "dui69hltsg2ds.cloudfront.net"

# Frontend app CloudFront (app.bluemoxon.com)
app_cloudfront_domain_name = "d2yd5bvqaomg54.cloudfront.net"

# API Gateway custom domain (api.bluemoxon.com)
api_gateway_domain_name    = "d-2bb05h3tf4.execute-api.us-west-2.amazonaws.com"
api_gateway_domain_zone_id = "Z2OJLYMUO9EFXC"

# Staging frontend CloudFront (staging.app.bluemoxon.com) - in staging account
staging_app_cloudfront_domain_name = "d3rkfi55tpd382.cloudfront.net"

# Staging API Gateway (staging.api.bluemoxon.com) - in staging account
staging_api_gateway_domain_name    = "d-3h13fsi1vl.execute-api.us-west-2.amazonaws.com"
staging_api_gateway_domain_zone_id = "Z2OJLYMUO9EFXC"
