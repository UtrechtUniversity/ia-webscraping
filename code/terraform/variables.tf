# This file declares terraform variables that are used in the main file
# Values are assigned in the terraform.tfvars file


variable "lambda_name" {
  description = "name of the lambda function that collects CDX records from the Internet Archive"
  type        = string
  default     = "my_lambda"
}

variable "result_bucket" {
  description = "name of the s3 bucket where scraping results stored"
  type        = string
  default     = "my_result_bucket"
}

variable "result_bucket_folder" {
  description = "name of the folder in which scraping results will be stored, this works with the result_bucket variable"
  type        = string
  default     = ""
}

variable "code_bucket" {
  description = "name of the s3 bucket where lambda zip and tfstate are stored"
  type        = string
  default     = "my_code_bucket"
}

variable "cdx_logging_level" {
  description = "set the log level, log messages which are less severe than level will be ignored"
  type        = string
  default     = "info"
  validation {
    condition     = var.cdx_logging_level == "info" || var.cdx_logging_level == "error"
    error_message = "Allowed values are: 'info' or 'error'."
  }
}

variable "scraper_logging_level" {
  description = "set the log level, log messages which are less severe than level will be ignored"
  type        = string
  default     = "info"
  validation {
    condition     = var.scraper_logging_level == "info" || var.scraper_logging_level == "error"
    error_message = "Allowed values are: 'info' or 'error'."
  }
}

variable "custom_log_group" {
  description = "AWS log group for metrics"
  type        = string
  default     = "my_log_group"
}

variable "custom_log_stream_cdx" {
  description = "custom log stream for CDX metrics"
  type        = string
  default     = "my_cdx_log_stream"
}

variable "custom_log_stream_scrape" {
  description = "custom log stream for scrape metrics"
  type        = string
  default     = "my_scrape_log_stream"
}

variable "sqs_fetch_limit" {
  description = "max number of allowed messages in Fetch SQS queue. When this limit is reached, no new messages are added"
  type        = string
  default     = "100000"
}

variable "sqs_cdx_max_messages" {
  description = "the max number of messages received from the CDX SQS queue in 1 iteration"
  type        = string
  default     = "10"
}

variable "cdx_lambda_n_iterations" {
  description = "the number of iterations the CDX function runs. Every iteration the cdx function processes max N='sqs_cdx_max_messages' messages"
  type        = string
  default     = "20"
}

variable "cdx_run_id" {
  description = "the ID of the crunchbase scrape run; this will be added as identifier to the cdx metrics logged in cloudwatch"
  type        = string
  default     = "1"
}

variable "ia_payload_year_from" {
  description = "starting year parameter form Internet Archive request payload"
  type        = string
  default     = "2018"
}

variable "ia_payload_year_to" {
  description = "end year parameter form Internet Archive request payload"
  type        = string
  default     = "2022"
}

variable "match_exact_url" {
  description = "match only the exact URL provided (ignores presence or absence of 'www.')"
  type        = string
  default     = "0"
}

variable "formats_to_save" {
  description = "file formats to export (possible values: txt,links,html)"
  type        = string
  default     = "txt,links"
}

variable "url_limit_per_domain" {
  description = "max. number of URLs to fetch from a single domain"
  type        = number
  default     = 1000
}

variable "sqs_message_author" {
  description = "author of messages in SQS queue"
  type        = string
  default     = "author"
}




variable "deployment_name" {
  description = "The name of the terraform deployment. This name is used for all resources."
  default     = "author"
}

variable "s3_destination_bucket_arn" {
  description = "The S3 destination bucket."
  default     = "author"
}

variable "s3_destination_bucket" {
  description = "The S3 destination bucket."
  default     = "author"
}

variable "glue_catalog_database_name" {
  description = "The Glue catalog database name"
  type        = string
  default     = "author"
}

variable "glue_catalog_table_name" {
  description = "The Glue catalog database table name"
  type        = string
  default     = "author"
}

variable "iam_role_lambda_scrape_name" {
  description = "The IAM Role name of the Lambda Scrape function that sends data to Kinesis Firehose."
  type        = string
  default     = "author"
}
