variable "lambda_name" {
     description = "name of the lambda function"
     type = string
     default = "my_lambda"
 } 

variable "bucket_name" {
     description = "name of the s3 bucket where lambda zip and tfstate are stored"
     type = string
     default = "s3-crunch-mvos"
 } 

  variable "env_vars" {
     description = "environment variables that lambda has access to"
     type = map
     default = {}
 } 

 variable "policy_file" {
     description = "name of file describing lambda policy"
     type = string
     default = "my_policy.json"
 } 

   variable "policy_vars" {
     description = "variables in policy file for specific lambda"
     type = map
     default = {}
 } 