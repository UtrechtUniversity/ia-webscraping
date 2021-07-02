

# Create bucket
resource "aws_s3_bucket" "result_bucket" {
  bucket = "crunchbase-scraping-results-csk" # bucket name
  acl    = "private"

  tags = {
    Name        = "scraping-result-bucket"
    Environment = "Dev"
  }
}

################################
### LAMBDA FUNCTIONS ###
################################

module "lambda_cdx" {
    source = "./lambda"
    lambda_name = "${var.lambda_name}-cdx" 
    bucket_name = "crunchbase-dev-mvos-source"
    policy_file = "cdx_lambda_policy.json"

    policy_vars = {
      sqs_arn = module.sqs_fetch.sqs_arn
      }

    env_vars = {
      sqs_cdx_id = module.sqs_cdx.sqs_id,
      sqs_cdx_arn = module.sqs_cdx.sqs_arn,
      sqs_message_delay_increase = var.sqs_message_delay_increase,
      sqs_cdx_max_messages = var.sqs_cdx_max_messages,
      cdx_lambda_n_iterations = var.cdx_lambda_n_iterations,
      cdx_logging_level = var.cdx_logging_level,
      cdx_run_id = var.cdx_run_id
        }
    }


module "lambda_scrape" {
    source = "./lambda"
    lambda_name = "${var.lambda_name}-scrape"
    bucket_name = "crunchbase-dev-mvos-source"
    policy_file = "scrape_lambda_policy.json"

  policy_vars = {
    sqs_arn = module.sqs_fetch.sqs_arn
    }

  env_vars = {
      sqs_fetch_id = module.sqs_fetch.sqs_id,
      sqs_fetch_arn = module.sqs_fetch.sqs_arn,
      target_bucket_id = aws_s3_bucket.result_bucket.id,
      sqs_fetch_limit = var.sqs_fetch_limit,
      sqs_message_delay_increase = var.sqs_message_delay_increase,
      sqs_failures_id = module.scrape_failures.sqs_id,
      sqs_failures_arn = module.scrape_failures.sqs_arn,
      scraper_logging_level = var.scraper_logging_level
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
  source    = "./sqs"
  sqs_name  = "${var.lambda_name}-fetch-queue"
  visibility_timeout_seconds = 120
  redrive_policy = jsonencode({
    deadLetterTargetArn = module.scrape_letters.sqs_arn
    maxReceiveCount     = 1000
  })
}

module "scrape_letters" {
  source    = "./sqs"
  sqs_name  = "scrape_lambda_dead_letters"
  delay_seconds = 90
}

module "scrape_failures" {
  source    = "./sqs"
  sqs_name  = "scrape_failures"
  delay_seconds  = 90
}


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
  batch_size       = 5 # set the amount of messages send to the lambda
  event_source_arn = module.sqs_fetch.sqs_arn
  enabled          = true
  function_name    = module.lambda_scrape.lambda_arn
  depends_on = [module.lambda_scrape.lambda_policy]# let's see if this works
}

#################################
###    Cloudwatch Trigger     ###
#################################

module "cloudwatch_trigger" {
    source = "./cloudwatch_trigger"
    lambda_name = module.lambda_cdx.lambda_name
    lambda_arn = module.lambda_cdx.lambda_arn
    trigger_rate = "3"
}