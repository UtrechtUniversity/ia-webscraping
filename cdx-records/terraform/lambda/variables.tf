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

   variable "sqs_fetch_arn" {
     description = "The ARN of the SQS queue which lists all fetch tasks"
     type = string
     default = "my_queue"
 } 