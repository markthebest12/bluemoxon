# Backend configuration
# Initialize with: terraform init -backend-config="key=bluemoxon/${ENV}/terraform.tfstate"
#
# Example:
#   terraform init -backend-config="key=bluemoxon/staging/terraform.tfstate"
#   terraform init -backend-config="key=bluemoxon/prod/terraform.tfstate"

terraform {
  backend "s3" {
    bucket         = "bluemoxon-terraform-state"
    region         = "us-west-2"
    encrypt        = true
    dynamodb_table = "bluemoxon-terraform-locks"
    # key is set via -backend-config during init
  }
}
