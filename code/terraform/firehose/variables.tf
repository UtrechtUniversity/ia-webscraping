variable "deployment_name" {
  description = "The name of the terraform deployment. This name is used for all resources."
}

variable "s3_destination_bucket_arn" {
  description = "The S3 destination bucket."
}

variable "s3_destination_bucket" {
  description = "The S3 destination bucket."
}

variable "glue_catalog_database_name" {
  description = "The Glue catalog database name"
  type        = string
}

variable "glue_catalog_table_name" {
  description = "The Glue catalog database table name"
  type        = string
}

variable "iam_role_lambda_scrape_name" {
  description = "The IAM Role name of the Lambda Scrape function that sends data to Kinesis Firehose."
  type        = string
}
