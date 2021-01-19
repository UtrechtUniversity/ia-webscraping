terraform {
  # variables are not allowed here
  backend "s3" {
    encrypt        = "true"
    bucket         = "terraform-crunchbase-surf-frankfurt"
    region         = "eu-central-1"
    profile        = "crunch"
    # change the key for any new cluster: terraform/state/<newkey>/terraform.tfstate
    # uncomment the following key
    key = "terraform/state/crunchbase_rjbood_lambda_example/terraform.tfstate"
  }
}
