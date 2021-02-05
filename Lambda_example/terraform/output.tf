output "sqs_id" {
    value = aws_sqs_queue.sqs_example_queue.id
    description = "The URL for the created Amazon SQS queue of the Lambda Example."
}

output "sqs_arn" {
    value = aws_sqs_queue.sqs_example_queue.arn
    description = "The ARN of the SQS queue of the Lambda Example."
}

output "cloudwatch_event_rule_arn" {
    value = module.cloudwatch_trigger.cloudwatch_event_rule_arn
    description = "The ARN of the cloudwatch event rule"
}
