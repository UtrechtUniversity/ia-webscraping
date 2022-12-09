output "kinesis_stream_arn" {
  value       = aws_kinesis_firehose_delivery_stream.s3_stream.arn
  description = "The ARN of the Kinesis stream."
}
