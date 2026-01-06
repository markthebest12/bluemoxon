bucket         = "bluemoxon-terraform-state"
region         = "us-west-2"
encrypt        = true
dynamodb_table = "bluemoxon-terraform-locks-prod"
key            = "bluemoxon/prod/terraform.tfstate"
