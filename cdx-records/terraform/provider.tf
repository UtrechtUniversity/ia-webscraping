provider "aws" {
  # Warning: Version constraints inside provider configuration blocks are deprecated
  # version                 = "~> 3.21"
  region  = "eu-central-1"
  profile = "crunch"
}
