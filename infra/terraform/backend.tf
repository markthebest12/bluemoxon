# Backend configuration (partial - values provided via backend config files)
#
# Each environment has its own S3 bucket and DynamoDB table for complete isolation:
#   - Staging: bluemoxon-terraform-state-staging (account 652617421195)
#   - Production: bluemoxon-terraform-state (account 266672885920)
#
# Initialize with environment-specific backend config:
#   AWS_PROFILE=bmx-staging terraform init -backend-config=backends/staging.hcl -reconfigure
#   AWS_PROFILE=bmx-prod terraform init -backend-config=backends/prod.hcl -reconfigure
#
# Then run plan/apply:
#   AWS_PROFILE=bmx-staging terraform plan -var-file=envs/staging.tfvars
#   AWS_PROFILE=bmx-prod terraform plan -var-file=envs/prod.tfvars

terraform {
  backend "s3" {
    # All values provided via -backend-config flag at init time
    # See backends/staging.hcl and backends/prod.hcl
  }
}
