provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "bluemoxon"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
