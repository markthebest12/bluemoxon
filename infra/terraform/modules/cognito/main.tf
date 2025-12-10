# =============================================================================
# Cognito User Pool Module
# =============================================================================

resource "aws_cognito_user_pool" "this" {
  name = var.user_pool_name

  # Username configuration
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  # Password policy
  password_policy {
    minimum_length                   = var.password_minimum_length
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = var.password_require_symbols
    require_uppercase                = true
    temporary_password_validity_days = 7
  }

  # MFA configuration
  mfa_configuration = var.mfa_configuration

  dynamic "software_token_mfa_configuration" {
    for_each = var.mfa_totp_enabled ? [1] : []
    content {
      enabled = true
    }
  }

  # Account recovery
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # Email configuration
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  # Admin create user config
  dynamic "admin_create_user_config" {
    for_each = var.allow_admin_create_user_only || var.invite_email_message != null ? [1] : []
    content {
      allow_admin_create_user_only = var.allow_admin_create_user_only

      dynamic "invite_message_template" {
        for_each = var.invite_email_message != null ? [1] : []
        content {
          email_message = var.invite_email_message
          email_subject = var.invite_email_subject
        }
      }
    }
  }

  # Schema attributes
  schema {
    name                     = "email"
    attribute_data_type      = "String"
    required                 = true
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  tags = var.tags

  # Lifecycle rule to prevent updates that would fail due to AWS validation quirks
  # AWS UpdateUserPool API requires SMS message in invite_message_template even when
  # SMS is not configured. This causes updates to fail when prod has custom invite templates.
  # Ignore all changes to user pool once imported to avoid this issue.
  lifecycle {
    ignore_changes = all
  }
}

# =============================================================================
# User Pool Client
# =============================================================================

resource "aws_cognito_user_pool_client" "this" {
  name         = coalesce(var.user_pool_client_name_override, "${var.user_pool_name}-client")
  user_pool_id = aws_cognito_user_pool.this.id

  # Note: Do NOT set generate_secret for existing clients without secrets.
  # Setting generate_secret = false forces replacement even when client has no secret.

  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]

  supported_identity_providers = ["COGNITO"]

  callback_urls = var.callback_urls
  logout_urls   = var.logout_urls

  allowed_oauth_flows                  = var.enable_oauth ? ["code"] : []
  allowed_oauth_scopes                 = var.enable_oauth ? ["email", "openid", "profile"] : []
  allowed_oauth_flows_user_pool_client = var.enable_oauth

  access_token_validity  = var.access_token_validity
  id_token_validity      = var.id_token_validity
  refresh_token_validity = var.refresh_token_validity

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }
}

# =============================================================================
# User Pool Domain (optional)
# =============================================================================

resource "aws_cognito_user_pool_domain" "this" {
  count        = var.domain_prefix != null ? 1 : 0
  domain       = var.domain_prefix
  user_pool_id = aws_cognito_user_pool.this.id
}
