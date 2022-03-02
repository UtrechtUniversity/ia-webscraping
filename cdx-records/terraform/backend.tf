terraform {
  # variables are not allowed here
  backend "s3" {
    encrypt = "true"
    bucket  = "iascraping"
    region  = "eu-central-1"
    profile = "crunch"
    # change the key for any new cluster: terraform/state/<newkey>/terraform.tfstate
    # uncomment the following key
    key = "terraform/state/whatever/terraform.tfstate"
  }
}
