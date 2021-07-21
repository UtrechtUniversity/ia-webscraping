output "sqs_cdx_id" {
  value       = module.sqs_cdx.sqs_id
  description = "The URL for the created Amazon SQS queue of the Lambda cdx function."
}

output "sqs_cdx_arn" {
  value       = module.sqs_cdx.sqs_arn
  description = "The ARN of the SQS queue of the Lambda cdx function."
}

output "sqs_fetch_id" {
  value       = module.sqs_fetch.sqs_id
  description = "The URL for the created Amazon SQS queue of the Lambda fetch function."
}

output "sqs_fetch_arn" {
  value       = module.sqs_fetch.sqs_arn
  description = "The ARN of the SQS queue which lists all fetch tasks."
}
