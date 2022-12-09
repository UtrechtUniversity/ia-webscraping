resource "aws_sqs_queue" "sqs_queue" {
  name                       = var.sqs_name
  delay_seconds              = var.delay_seconds
  redrive_policy             = var.redrive_policy
  # max_message_size           = 2048
  max_message_size           = 8192
  # message_retention_seconds  = 86400
  message_retention_seconds  = 1209600
  receive_wait_time_seconds  = var.receive_wait_time_seconds
  visibility_timeout_seconds = var.visibility_timeout_seconds
}
