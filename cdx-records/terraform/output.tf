output "sqs_cdx_id" {
    value = aws_sqs_queue.sqs_cdx_queue.id
    description = "The URL for the created Amazon SQS queue of the Lambda cdx function."
}

output "sqs_cdx_arn" {
    value = aws_sqs_queue.sqs_cdx_queue.arn
    description = "The ARN of the SQS queue of the Lambda cdx function."
}

output "sqs_fetch_id" {
    value = aws_sqs_queue.sqs_fetch_queue.id
    description = "The URL for the created Amazon SQS queue of the Lambda fetch function."
}

output "sqs_fetch_arn" {
    value = aws_sqs_queue.sqs_fetch_queue.arn
    description = "The ARN of the SQS queue of the Lambda fetch function."
}