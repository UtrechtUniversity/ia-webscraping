<!-- BEGIN_TF_DOCS -->
## Requirements

No requirements.

## Providers

| Name | Version |
|------|---------|
| <a name="provider_aws"></a> [aws](#provider\_aws) | n/a |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [aws_glue_catalog_database.glue_catalog_database](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glue_catalog_database) | resource |
| [aws_glue_catalog_table.glue_catalog_table](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glue_catalog_table) | resource |
| [aws_iam_role.firehose_role](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role) | resource |
| [aws_iam_role_policy.kinesis_firehose_access_glue_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy) | resource |
| [aws_iam_role_policy.kinesis_put](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy) | resource |
| [aws_iam_role_policy.s3_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy) | resource |
| [aws_kinesis_firehose_delivery_stream.s3_stream](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kinesis_firehose_delivery_stream) | resource |
| [aws_iam_policy_document.kinesis_firehose_access_glue_assume_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_iam_policy_document.kinesis_put](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_iam_policy_document.s3_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_deployment_name"></a> [deployment\_name](#input\_deployment\_name) | The name of the terraform deployment. This name is used for all resources. | `any` | n/a | yes |
| <a name="input_glue_catalog_database_name"></a> [glue\_catalog\_database\_name](#input\_glue\_catalog\_database\_name) | The Glue catalog database name | `string` | n/a | yes |
| <a name="input_glue_catalog_table_name"></a> [glue\_catalog\_table\_name](#input\_glue\_catalog\_table\_name) | The Glue catalog database table name | `string` | n/a | yes |
| <a name="input_iam_role_lambda_scrape_name"></a> [iam\_role\_lambda\_scrape\_name](#input\_iam\_role\_lambda\_scrape\_name) | The IAM Role name of the Lambda Scrape function that sends data to Kinesis Firehose. | `string` | n/a | yes |
| <a name="input_s3_destination_bucket"></a> [s3\_destination\_bucket](#input\_s3\_destination\_bucket) | The S3 destination bucket. | `any` | n/a | yes |
| <a name="input_s3_destination_bucket_arn"></a> [s3\_destination\_bucket\_arn](#input\_s3\_destination\_bucket\_arn) | The S3 destination bucket. | `any` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_kinesis_stream_arn"></a> [kinesis\_stream\_arn](#output\_kinesis\_stream\_arn) | The ARN of the Kinesis stream. |
<!-- END_TF_DOCS -->