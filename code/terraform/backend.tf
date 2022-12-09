terraform {
  backend "s3" {
    encrypt = "true"
    bucket  = "crunchbase-prod-code"
    region  = "eu-central-1"
    profile = "crunch"
    key = "terraform/state/crunchbase/terraform.tfstate"
  }
}
