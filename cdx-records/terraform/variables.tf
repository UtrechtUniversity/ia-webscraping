# This file declares terraform variables that are used in the main file
# Values are assigned in the terraform.tfvars file


# CDX LAMBDA: settings

 variable "lambda_cdx" {
     description = "name of the lambda function that collects CDX records from the Internet Archive"
     type = string
     default = "lambda-cdx-crunchbase-dev-mvos"
 } 

 variable "bucket_name" {
     description = "name of the s3 bucket where lambda zip and tfstate are stored"
     type = string
     default = "crunchbase-dev-mvos-source"
 } 

 variable "cdx_logging_level" {
     description = "set the log level, log messages which are less severe than level will be ignored"
     type = string
     default = "error"
     validation {
        condition = var.cdx_logging_level == "info" || var.cdx_logging_level == "error" 
        error_message = "Allowed values are: 'info' or 'error'."
     }
 }

  variable "scraper_logging_level" {
     description = "set the log level, log messages which are less severe than level will be ignored"
     type = string
     default = "error"
     validation {
        condition = var.scraper_logging_level == "info" || var.scraper_logging_level == "error" 
        error_message = "Allowed values are: 'info' or 'error'."
     }
 }

 variable "sqs_fetch_limit" {
     description = "max number of allowed messages in Fetch SQS queue. When this limit is reached, no new messages are added"
     type = string
     default = "1000"
 }

 variable "sqs_message_delay_increase" {
     description = "the delay time (sec) that should be added to every batch of 30 sqs fetch messages"
     type = string
     default = "10"
 }

 variable "sqs_cdx_max_messages" {
     description = "the max number of messages received from the CDX SQS queue in 1 iteration"
     type = string
     default = "10"
 } 

 variable "cdx_lambda_n_iterations" {
     description = "the number of iterations the CDX function runs. Every iteration the cdx function processes max N='sqs_cdx_max_messages' messages"
     type = string
     default = "2"
 } 

 variable "cdx_run_id" {
     description = "the ID of the crunchbase scrape run; this will be added as identifier to the cdx metrics logged in cloudwatch"
     type = string
     default = "1"
 } 

