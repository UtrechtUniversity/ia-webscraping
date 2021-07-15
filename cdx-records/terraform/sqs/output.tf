output "sqs_id" {
    value = aws_sqs_queue.sqs_queue.id
    description = "The id of the sqs queue, to be used in main"
}

output "sqs_arn" {
    value = aws_sqs_queue.sqs_queue.arn
    description = "The ARN of the sqs queue, to be used in main"
}

