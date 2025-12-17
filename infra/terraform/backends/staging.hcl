bucket         = "bluemoxon-terraform-state-staging"
region         = "us-west-2"
encrypt        = true
dynamodb_table = "bluemoxon-terraform-lock-staging"
key            = "bluemoxon/staging/terraform.tfstate"
