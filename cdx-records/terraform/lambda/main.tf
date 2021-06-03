data "aws_s3_bucket_object" "lambda_code" {
  bucket = var.bucket_name
  key    = "cdx-records/${var.lambda_name}.zip"
}

# List specific lambda policy in this file
data "template_file" "policy" {
  template = "${file("${path.module}/cdx_lambda_policy.json")}"
  
vars = {
    sqs_fetch_id = "${var.sqs_fetch_id}"
  }
}

resource "aws_lambda_function" "lambda" {
  function_name = var.lambda_name
  description = "aws lambda function"
  role          = aws_iam_role.iam_role_lambda.arn

  s3_bucket = data.aws_s3_bucket_object.lambda_code.bucket
  s3_key = data.aws_s3_bucket_object.lambda_code.key

  handler       = "main.handler"

  # Check hash code for code changes
  source_code_hash = chomp(file("../${var.lambda_name}.zip.sha256"))

  runtime = "python3.8"
  timeout = 120
  memory_size = "128"

  environment {
    variables = var.env_vars
  }
}

resource "aws_iam_role" "iam_role_lambda" {
  name = var.lambda_name
  assume_role_policy = file("${path.module}/trust_relationship.json")
}

resource "aws_iam_policy" "policy_lambda" {
  name = "policy_${var.lambda_name}"
  policy = "${data.template_file.policy.rendered}"
}

resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  role   = aws_iam_role.iam_role_lambda.name
  policy_arn = aws_iam_policy.policy_lambda.arn
}

