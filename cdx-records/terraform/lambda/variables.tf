variable "lambda_function" {
  description = "name of the lambda function"
  type        = string
  default     = "my_lambda"
}

variable "bucket_name" {
  description = "name of the s3 bucket where lambda zip and tfstate are stored"
  type        = string
  default     = "s3-crunch-mvos"
}

variable "env_vars" {
  description = "environment variables that lambda has access to"
  type        = map(any)
  default     = {}
}

variable "policy" {
  description = "An additional policy to attach to the Lambda function role"
  type = object({
    json = string
  })
  default = null
}