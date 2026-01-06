bucket         = "bluemoxon-terraform-state-staging"
region         = "us-west-2"
encrypt        = true
dynamodb_table = "bluemoxon-terraform-locks-staging"
key            = "bluemoxon/staging/terraform.tfstate"
