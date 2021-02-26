# This file declares terraform variables that are used in the main file
# Values are assigned in the assign.tfvars file

variable "bucket_name" {
    type = string
}

variable "lambda_name" {
    type = string
}

variable "profile" {
    type = string
}