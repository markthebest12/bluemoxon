# =============================================================================
# TFLint Configuration
# =============================================================================
# Run with: tflint --init && tflint
# =============================================================================

config {
  # Enable module inspection
  call_module_type = "local"
}

# =============================================================================
# Plugins
# =============================================================================

plugin "aws" {
  enabled = true
  version = "0.31.0"
  source  = "github.com/terraform-linters/tflint-ruleset-aws"
}

plugin "terraform" {
  enabled = true
  version = "0.6.0"
  source  = "github.com/terraform-linters/tflint-ruleset-terraform"
  preset  = "recommended"
}

# =============================================================================
# AWS Rules
# =============================================================================

# Ensure instance types are valid
rule "aws_instance_invalid_type" {
  enabled = true
}

# Ensure RDS instance classes are valid
rule "aws_db_instance_invalid_type" {
  enabled = true
}

# Warn about default VPC usage
rule "aws_instance_default_vpc" {
  enabled = true
}

# =============================================================================
# Terraform Rules
# =============================================================================

# Enforce naming conventions
rule "terraform_naming_convention" {
  enabled = true
  format  = "snake_case"
}

# Require descriptions for variables and outputs
rule "terraform_documented_variables" {
  enabled = true
}

rule "terraform_documented_outputs" {
  enabled = true
}

# Enforce consistent formatting
rule "terraform_standard_module_structure" {
  enabled = true
}

# Warn about deprecated syntax
rule "terraform_deprecated_index" {
  enabled = true
}

rule "terraform_deprecated_interpolation" {
  enabled = true
}

# Require type declarations for variables
rule "terraform_typed_variables" {
  enabled = true
}
