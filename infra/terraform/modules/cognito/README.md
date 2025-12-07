# Cognito Module

Creates a Cognito User Pool with email-based authentication, OAuth configuration, and optional hosted UI domain.

## Usage

```hcl
module "auth" {
  source = "./modules/cognito"

  user_pool_name = "my-app-users"
  domain_prefix  = "my-app"
  enable_oauth   = true

  callback_urls = [
    "https://app.example.com/auth/callback",
    "http://localhost:5173/auth/callback"
  ]
  logout_urls = [
    "https://app.example.com",
    "http://localhost:5173"
  ]

  tags = {
    Environment = "production"
  }
}
```

## Requirements

| Name | Version |
|------|---------|
| terraform | >= 1.6.0 |
| aws | ~> 5.0 |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| access_token_validity | Access token validity in hours | `number` | `1` | no |
| callback_urls | Callback URLs for OAuth | `list(string)` | `[]` | no |
| domain_prefix | Cognito domain prefix | `string` | `null` | no |
| enable_oauth | Enable OAuth flows | `bool` | `false` | no |
| id_token_validity | ID token validity in hours | `number` | `1` | no |
| logout_urls | Logout URLs for OAuth | `list(string)` | `[]` | no |
| mfa_configuration | MFA configuration: OFF, ON, or OPTIONAL | `string` | `"OFF"` | no |
| mfa_totp_enabled | Enable TOTP (software token) MFA | `bool` | `false` | no |
| password_minimum_length | Minimum password length | `number` | `8` | no |
| password_require_symbols | Require symbols in password | `bool` | `true` | no |
| refresh_token_validity | Refresh token validity in days | `number` | `30` | no |
| tags | Resource tags | `map(string)` | `{}` | no |
| user_pool_name | Name of the Cognito user pool | `string` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| client_id | ID of the user pool client |
| domain | Cognito domain (if configured) |
| user_pool_arn | ARN of the Cognito user pool |
| user_pool_endpoint | Endpoint of the Cognito user pool |
| user_pool_id | ID of the Cognito user pool |
