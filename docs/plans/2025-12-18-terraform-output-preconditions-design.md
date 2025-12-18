# Terraform Output Preconditions Design

**Date:** 2025-12-18
**Status:** Approved
**Related Issue:** #422 (Production Cognito config empty)

## Problem

When `enable_cognito = false` (or similar flags), Terraform outputs were returning `null` instead of using the `*_external` fallback variables. This caused production frontend to receive empty Cognito configuration, breaking authentication.

## Goal

Fail fast at Terraform plan/apply time when external fallback values are required but not provided.

## Design Decisions

1. **Mechanism:** Terraform `precondition` blocks on output definitions
2. **Scope:** All 5 external fallback outputs
3. **Validation:** Non-null and non-empty string check

## Implementation

### Pattern

```hcl
output "example_output" {
  description = "Example output with external fallback"
  value       = var.enable_example ? module.example[0].value : var.example_external

  precondition {
    condition     = var.enable_example || (var.example_external != null && var.example_external != "")
    error_message = "example_external must be set when enable_example is false"
  }
}
```

### Outputs to Update

| Output | Enable Flag | External Variable |
|--------|-------------|-------------------|
| `cognito_user_pool_id` | `enable_cognito` | `cognito_user_pool_id_external` |
| `cognito_client_id` | `enable_cognito` | `cognito_client_id_external` |
| `cognito_domain` | `enable_cognito` | `cognito_domain_override` |
| `lambda_function_name` | `enable_lambda` | `lambda_function_name_external` |
| `lambda_invoke_arn` | `enable_lambda` | `lambda_invoke_arn_external` |

### cognito_user_pool_id

```hcl
output "cognito_user_pool_id" {
  description = "Cognito user pool ID"
  value       = var.enable_cognito ? module.cognito[0].user_pool_id : var.cognito_user_pool_id_external

  precondition {
    condition     = var.enable_cognito || (var.cognito_user_pool_id_external != null && var.cognito_user_pool_id_external != "")
    error_message = "cognito_user_pool_id_external must be set when enable_cognito is false"
  }
}
```

### cognito_client_id

```hcl
output "cognito_client_id" {
  description = "Cognito app client ID"
  value       = var.enable_cognito ? module.cognito[0].client_id : var.cognito_client_id_external

  precondition {
    condition     = var.enable_cognito || (var.cognito_client_id_external != null && var.cognito_client_id_external != "")
    error_message = "cognito_client_id_external must be set when enable_cognito is false"
  }
}
```

### cognito_domain

```hcl
output "cognito_domain" {
  description = "Cognito domain (full auth domain)"
  value = var.enable_cognito ? (
    module.cognito[0].domain != null ? "${module.cognito[0].domain}.auth.${data.aws_region.current.name}.amazoncognito.com" : null
    ) : (
    var.cognito_domain_override != null ? "${var.cognito_domain_override}.auth.${data.aws_region.current.name}.amazoncognito.com" : null
  )

  precondition {
    condition     = var.enable_cognito || (var.cognito_domain_override != null && var.cognito_domain_override != "")
    error_message = "cognito_domain_override must be set when enable_cognito is false"
  }
}
```

### lambda_function_name

```hcl
output "lambda_function_name" {
  description = "Lambda function name"
  value       = var.enable_lambda ? module.lambda[0].function_name : var.lambda_function_name_external

  precondition {
    condition     = var.enable_lambda || (var.lambda_function_name_external != null && var.lambda_function_name_external != "")
    error_message = "lambda_function_name_external must be set when enable_lambda is false"
  }
}
```

### lambda_invoke_arn

```hcl
output "lambda_invoke_arn" {
  description = "Lambda invoke ARN"
  value       = var.enable_lambda ? module.lambda[0].invoke_arn : var.lambda_invoke_arn_external

  precondition {
    condition     = var.enable_lambda || (var.lambda_invoke_arn_external != null && var.lambda_invoke_arn_external != "")
    error_message = "lambda_invoke_arn_external must be set when enable_lambda is false"
  }
}
```

## Testing Approach

### Manual Verification

```bash
cd infra/terraform

# 1. Temporarily break config
sed -i.bak 's/^cognito_user_pool_id_external/#cognito_user_pool_id_external/' envs/prod.tfvars

# 2. Run plan - should FAIL with clear error
AWS_PROFILE=bmx-prod terraform plan -var-file=envs/prod.tfvars -var="db_password=test"

# 3. Restore config
mv envs/prod.tfvars.bak envs/prod.tfvars
```

### Expected Behavior

| Scenario | Result |
|----------|--------|
| External value missing | Plan fails with clear error |
| External value empty string | Plan fails with clear error |
| External value set correctly | Plan succeeds normally |
| Module enabled (not external) | Precondition skipped |

## Files to Modify

- `infra/terraform/outputs.tf` - Add precondition blocks to 5 outputs

## Risks

- **Low:** Preconditions are evaluated at plan time, so no runtime impact
- **Low:** Only affects configurations where enable flag is false AND external value is missing
