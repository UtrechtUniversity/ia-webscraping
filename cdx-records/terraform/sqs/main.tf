resource "aws_sqs_queue" "sqs_queue" {
  name                       = var.sqs_name
  delay_seconds              = var.delay_seconds
  redrive_policy             = var.redrive_policy
  max_message_size           = 2048
  message_retention_seconds  = 86400
  receive_wait_time_seconds  = 10
  visibility_timeout_seconds = var.visibility_timeout_seconds
}
