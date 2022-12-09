# Create bucket
resource "aws_s3_bucket" "result_bucket" {
  bucket = var.result_bucket

  tags = {
    Name        = "scraping-result-bucket"
    Environment = "Dev"
  }
}

resource "aws_s3_bucket_acl" "result_bucket" {
  bucket = var.result_bucket
  acl    = "private"
}

################################
### LAMBDA POLICIES ###
################################

# Generate policy document for cdx lambda
data "aws_iam_policy_document" "cdx_policy" {
  statement {
    sid = "1"
    actions = [
      "sqs:SendMessage",
      "sqs:GetQueueAttributes",
    ]
    resources = [
      module.sqs_fetch.sqs_arn,
    ]
  }
  statement {
    sid = "2"
    actions = [
      "sqs:ListQueues",
    ]
    resources = [
      "*",
    ]
  }
  statement {
    sid = "3"

    actions = [
      "s3:GetObject",
      "s3:ListBucket",
      "s3:PutObject"
    ]

    resources = [
      "${aws_s3_bucket.result_bucket.arn}/*",
      "${aws_s3_bucket.result_bucket.arn}"
    ]
  }

  statement {
    sid = "4"

    actions = [
      "logs:CreateLogStream",
      "logs:CreateLogGroup",
      "logs:PutLogEvents",
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams"
    ]

    resources = [ "*" ]
  }


}



# Generate policy document for scrape lambda
data "aws_iam_policy_document" "scrape_policy" {
  statement {
    sid = "1"
    actions = [
      "sqs:DeleteMessage",
      "sqs:ReceiveMessage",
      "sqs:GetQueueAttributes",
    ]
    resources = [
      "${module.sqs_fetch.sqs_arn}",
    ]
  }
#  statement {
#    sid = "2"
#    actions = [
#      "sqs:SendMessage",
#    ]
#    resources = [
#      "${module.scrape_failures.sqs_arn}",
#    ]
#  }
  statement {
    sid = "3"
    actions = [
      "sqs:ListQueues",
    ]
    resources = [
      "*",
    ]
  }
  statement {
    sid = "4"
    actions = [
      "s3:PutObject",
    ]
    resources = [
      "${aws_s3_bucket.result_bucket.arn}/*",
    ]
  }


  statement {
    sid = "5"

    actions = [
      "logs:CreateLogStream",
      "logs:CreateLogGroup",
      "logs:PutLogEvents",
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams"
    ]

    resources = [ "*" ]
  }
}

################################
### LAMBDA FUNCTIONS ###
################################

module "lambda_cdx" {
  source          = "./lambda"
  lambda_function = "${var.lambda_name}-cdx"
  code_bucket     = var.code_bucket
  timeout         = 900

  policy = {
    json = data.aws_iam_policy_document.cdx_policy.json
  }

  env_vars = {
    sqs_cdx_id                 = module.sqs_cdx.sqs_id
    sqs_cdx_arn                = module.sqs_cdx.sqs_arn
    sqs_cdx_max_messages       = var.sqs_cdx_max_messages
    sqs_fetch_id               = module.sqs_fetch.sqs_id
    sqs_fetch_arn              = module.sqs_fetch.sqs_arn
    sqs_fetch_limit            = var.sqs_fetch_limit
    sqs_message_author         = var.sqs_message_author
    cdx_lambda_n_iterations    = var.cdx_lambda_n_iterations
    cdx_logging_level          = var.cdx_logging_level
    payload_from_year          = var.ia_payload_year_from
    payload_to_year            = var.ia_payload_year_to
    url_limit_per_domain       = var.url_limit_per_domain
    match_exact_url            = var.match_exact_url
  }
}

module "lambda_scrape" {
  source          = "./lambda"
  lambda_function = "${var.lambda_name}-scrape"
  code_bucket     = var.code_bucket

  policy = {
    json = data.aws_iam_policy_document.scrape_policy.json
  }

  env_vars = {
    sqs_fetch_id              = module.sqs_fetch.sqs_id
    sqs_fetch_arn             = module.sqs_fetch.sqs_arn
    scraper_logging_level     = var.scraper_logging_level
    formats_to_save           = var.formats_to_save
  }
}

#################################
###    SQS QUEUES    ###
#################################

module "sqs_cdx" {
  source   = "./sqs"
  sqs_name = "${var.lambda_name}-cdx-queue"
}

module "sqs_fetch" {
  source                     = "./sqs"
  sqs_name                   = "${var.lambda_name}-scrape-queue"
  visibility_timeout_seconds = 900
  receive_wait_time_seconds  = 1
  delay_seconds              = 1
  redrive_policy = jsonencode({
    deadLetterTargetArn = module.scrape_letters.sqs_arn
    maxReceiveCount     = 10
  })
}

module "scrape_letters" {
 source        = "./sqs"
 sqs_name      = "${var.lambda_name}-dead-letters"
 delay_seconds = 90
}

# module "scrape_failures" {
#   source        = "./sqs"
#   sqs_name      = "${var.lambda_name}-failures"
#   delay_seconds = 90
# }


# THIS MAKES THE sqs_fetch_queue TRIGGER THE scraping LAMBDA
# ##########################################################
resource "aws_lambda_permission" "allows_fetch_sqs_to_trigger_scraper_lambda" {
  statement_id  = "AllowExecutionFromSQS"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda_scrape.lambda_name
  principal     = "sqs.amazonaws.com"
  source_arn    = module.sqs_fetch.sqs_arn
}

resource "aws_lambda_event_source_mapping" "trigger_scraper" {
  batch_size = 10 # set the amount of messages send to the lambda
  # maximum_batching_window_in_seconds  = 30
  event_source_arn = module.sqs_fetch.sqs_arn
  enabled          = true
  function_name    = module.lambda_scrape.lambda_arn
  depends_on       = [module.lambda_scrape.lambda_policy] # let's see if this works
}

#################################
###    Cloudwatch Trigger     ###
#################################

module "cloudwatch_trigger" {
  source       = "./cloudwatch_trigger"
  lambda_name  = module.lambda_cdx.lambda_name
  lambda_arn   = module.lambda_cdx.lambda_arn
  trigger_rate = "2"
}


#################################
###    Kinesis Firehose       ###
#################################
module "crunch-firehose" {
  source = "./firehose"

  deployment_name             = "scrape"
  # s3_destination_bucket_arn   = "arn:aws:s3:::scrape"
  # s3_destination_bucket       = "crunchbase-dev-rjbood"
  s3_destination_bucket       = var.result_bucket
  s3_destination_bucket_arn   = "arn:aws:s3:::${var.result_bucket}"
  glue_catalog_database_name  = "scrape_results"
  glue_catalog_table_name     = "scrape_results"
  iam_role_lambda_scrape_name = "crunchbase-scrape"
}

output "kinesis_stream_arn" {
  value       = module.crunch-firehose.kinesis_stream_arn
  description = "The ARN of the Kinesis stream."
}
