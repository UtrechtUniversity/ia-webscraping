terraform {
  # variables are not allowed here
  backend "s3" {
    encrypt        = "true"
    bucket         = "crunchbase-dev-mvos-source"
    region         = "eu-central-1"
    profile        = "default"
    # change the key for any new cluster: terraform/state/<newkey>/terraform.tfstate
    # uncomment the following key
    key = "terraform/state/crunchbase-dev-mvos-lambda-cdx/terraform.tfstate"
  }
}
