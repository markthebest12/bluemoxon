# Terraform Output Preconditions Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add precondition blocks to 5 Terraform outputs that use external fallback values, ensuring plan/apply fails fast when required external values are missing.

**Architecture:** Terraform `precondition` blocks validate that when a module is disabled (`enable_X = false`), the corresponding external fallback variable is set. Validation happens at plan time before any infrastructure changes.

**Tech Stack:** Terraform 1.5+, AWS provider

---

## Task 1: Add precondition to cognito_user_pool_id output

**Files:**

- Modify: `infra/terraform/outputs.tf:35-38`

**Step 1: Read current output definition**

```bash
grep -A5 'output "cognito_user_pool_id"' infra/terraform/outputs.tf
```

**Step 2: Add precondition block**

Replace the `cognito_user_pool_id` output (lines 35-38) with:

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

**Step 3: Validate syntax**

Run: `terraform validate`
Expected: Success! The configuration is valid.

**Step 4: Commit**

```bash
git add infra/terraform/outputs.tf
git commit -m "infra: Add precondition to cognito_user_pool_id output"
```

---

## Task 2: Add precondition to cognito_client_id output

**Files:**

- Modify: `infra/terraform/outputs.tf:21-24`

**Step 1: Add precondition block**

Replace the `cognito_client_id` output (lines 21-24) with:

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

**Step 2: Validate syntax**

Run: `terraform validate`
Expected: Success! The configuration is valid.

**Step 3: Commit**

```bash
git add infra/terraform/outputs.tf
git commit -m "infra: Add precondition to cognito_client_id output"
```

---

## Task 3: Add precondition to cognito_domain output

**Files:**

- Modify: `infra/terraform/outputs.tf:26-33`

**Step 1: Add precondition block**

Replace the `cognito_domain` output (lines 26-33) with:

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

**Step 2: Validate syntax**

Run: `terraform validate`
Expected: Success! The configuration is valid.

**Step 3: Commit**

```bash
git add infra/terraform/outputs.tf
git commit -m "infra: Add precondition to cognito_domain output"
```

---

## Task 4: Add precondition to lambda_function_name output

**Files:**

- Modify: `infra/terraform/outputs.tf:79-82`

**Step 1: Add precondition block**

Replace the `lambda_function_name` output (lines 79-82) with:

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

**Step 2: Validate syntax**

Run: `terraform validate`
Expected: Success! The configuration is valid.

**Step 3: Commit**

```bash
git add infra/terraform/outputs.tf
git commit -m "infra: Add precondition to lambda_function_name output"
```

---

## Task 5: Add precondition to lambda_invoke_arn output

**Files:**

- Modify: `infra/terraform/outputs.tf:89-92`

**Step 1: Add precondition block**

Replace the `lambda_invoke_arn` output (lines 89-92) with:

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

**Step 2: Validate syntax**

Run: `terraform validate`
Expected: Success! The configuration is valid.

**Step 3: Commit**

```bash
git add infra/terraform/outputs.tf
git commit -m "infra: Add precondition to lambda_invoke_arn output"
```

---

## Task 6: Test preconditions catch missing values

**Files:**

- Temporarily modify: `infra/terraform/envs/prod.tfvars`

**Step 1: Temporarily comment out an external value**

```bash
sed -i.bak 's/^cognito_user_pool_id_external/#cognito_user_pool_id_external/' infra/terraform/envs/prod.tfvars
```

**Step 2: Run plan expecting failure**

Run: `AWS_PROFILE=bmx-prod terraform plan -var-file=envs/prod.tfvars -var="db_password=test" 2>&1 | head -30`

Expected output containing:

```
Error: Resource precondition failed
cognito_user_pool_id_external must be set when enable_cognito is false
```

**Step 3: Restore config**

```bash
mv infra/terraform/envs/prod.tfvars.bak infra/terraform/envs/prod.tfvars
```

**Step 4: Verify prod plan succeeds with config restored**

Run: `AWS_PROFILE=bmx-prod terraform plan -var-file=envs/prod.tfvars -var="db_password=test" 2>&1 | tail -5`

Expected: Plan shows no errors (may show changes if state differs)

---

## Task 7: Create PR

**Step 1: Push branch**

```bash
git push -u origin feat/terraform-output-preconditions
```

**Step 2: Create PR**

```bash
gh pr create --base staging --title "infra: Add preconditions to external fallback outputs" --body "$(cat <<'EOF'
## Summary
- Adds Terraform precondition blocks to 5 outputs that use external fallback values
- Ensures plan/apply fails fast when `enable_X = false` but external value is missing
- Prevents issue #422 (empty Cognito config in production) from recurring

## Outputs Updated
- `cognito_user_pool_id` - validates `cognito_user_pool_id_external`
- `cognito_client_id` - validates `cognito_client_id_external`
- `cognito_domain` - validates `cognito_domain_override`
- `lambda_function_name` - validates `lambda_function_name_external`
- `lambda_invoke_arn` - validates `lambda_invoke_arn_external`

## Test Plan
- [x] `terraform validate` passes
- [x] Plan fails when external value missing (tested by commenting out)
- [x] Plan succeeds when external values present

## Related
- Fixes prevention for #422
- Design: docs/plans/2025-12-18-terraform-output-preconditions-design.md

Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

**Step 3: Wait for CI**

```bash
gh pr checks --watch
```

---

## Summary

| Task | Description | Commit |
|------|-------------|--------|
| 1 | cognito_user_pool_id precondition | `infra: Add precondition to cognito_user_pool_id output` |
| 2 | cognito_client_id precondition | `infra: Add precondition to cognito_client_id output` |
| 3 | cognito_domain precondition | `infra: Add precondition to cognito_domain output` |
| 4 | lambda_function_name precondition | `infra: Add precondition to lambda_function_name output` |
| 5 | lambda_invoke_arn precondition | `infra: Add precondition to lambda_invoke_arn output` |
| 6 | Test preconditions | (no commit - validation only) |
| 7 | Create PR | Push + PR creation |
