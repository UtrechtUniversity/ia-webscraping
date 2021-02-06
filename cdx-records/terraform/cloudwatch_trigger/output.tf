output "cloudwatch_event_rule_arn" {
    value = aws_cloudwatch_event_rule.every_minute.arn
    description = "The ARN of the event rule"
}