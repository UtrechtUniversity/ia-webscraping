# ia-webscraping

This repository provides code to set up an AWS workflow for collecting and analyzing webpages from the Internet Archive.
It is developed for the Crunchbase project to assess the sustainability of European startup-companies by analyzing their websites. 

This software is designed for users with prior knowledge of python, aws and infrastructure.

## Table of Contents

- [Project Title](#ia-webscraping)
  - [Table of Contents](#table-of-contents)
  - [About the Project](#about-the-project)
    - [Built with](#built-with)
    - [License](#license)
    - [Architecture](#architecture)
  - [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
  - [Usage](#usage)
    - [Deploy AWS resources](#deploy-aws-resources)
    - [Fill SQS queue ](#fill-sqs-queue)
    - [Test Function](#test-function)
    - [Clean Up](#clean-up)


## About the Project

**Date**: Jan-Jun 2021

**Researcher**:

- Jip Leendertse (j.leendertse@uu.nl)

**Research Software Engineer**:

- Casper Kaandorp (c.s.kaandorp@uu.nl)
- Martine de Vos (m.g.devos@uu.nl)
- Robert Jan Bood (robert-jan.bood@surf.nl)

This project is part of the Public Cloud call of [SURF](https://www.surf.nl/en/) 

### Built with

- [Terraform](https://www.terraform.io/)
- [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [asyncio](https://docs.aiohttp.org/en/stable/glossary.html#term-asyncio)

### License

The code in this project is released under [MIT](LICENSE).

### Architecture
The ia-webscraping repository utilizes the following AWS services:
- **Simple Queueing System**: manage distribution of tasks among Lambda functions and give insight in results
    - queue with initial urls 
    - queue with scraping tasks
- **AWS Lambda**: run code without the need for provisioning or managing servers
    - lambda to retrieve cdx records for initial urls, filter these and send tasks to scraping queue 
    - lambda to retrieve webpages for cdx records and send these to s3 bucket
- **S3**: for storage of the HTML pages
- **CloudWatch**: monitor and manage AWS services
   - CloudWatch to monitor the metrics of the SQS queue and Lambda functions
   - CloudWatch to trigger the Lambda function on a timely basis, the interval can be changed to throttle the process

Deploying this solution will result in the following scrape pipeline in the AWS Cloud.

![Alt text](docs/architecture_overview.png?raw=true "Architecture Overview")

## Getting started

  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Build Lambda function](#build-lambda-functions)
  - [Update Terraform](#update-terraform)

### Prerequisites
To run this project you need to take the following steps:
- (optional) install package manager. 
	- windows: [chocolatey](https://chocolatey.org/install), 
	- mac: [brew](https://brew.sh)
	- With a package manager it becomes easy to install/update the below prerequisites. 
    For example:  ```choco install awscli' ```
- [install aws cli](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)
- [configure aws cli credentials](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)
    create a profile with the name 'crunch' 
- install python3 , pip3 , pandas, boto3
- install [terraform](https://www.terraform.io/downloads.html)
- create a personal S3 bucket in AWS (region: eu-central-1)

### Installation
Create your own copy of the 'cdx-records' directory on your local client.

### Build lambda functions
The 'build.sh' script will for each of the lambda functions:
- install all requirements from the 'requirements.txt' file in the lambda folder
- create a zip file 
- calculate a hash of this zipfile and write this to 'example_lambda.zip.sha256'
- upload the zip file to the s3 bucket

First update the build script
- line 16: provide your AWS bucket name (see [Prerequisites](#prerequisites))

Then run the build script
```
# Go to terraform folder
$ cd cdx-records

# Build zip files
$ ./build.sh 
```

### Update Terraform

In the [terraform folder](/cdx-records/terraform) create a file ```terraform.tfvars``` that lists the below terraform variables and the corresponding values.
See [variables file](/cdx-records/terraform/variables.tf) for more information on the variables.

```
code_bucket = [YOUR_BUCKET_NAME]

result_bucket = [YOUR_BUCKET_NAME]

lambda_name = [YOUR_LAMBDA_NAME]

------- Optional: when not specified the default applies -----------

cdx_logging_level = [CDX_DEBUG_LEVEL; DEFAULT=error]

scraper_logging_level = [SCRAPER_DEBUG_LEVEL; DEFAULT=error]

sqs_fetch_limit = [MAX_MESSAGES_FETCH_QUEUE; DEFAULT=1000]

sqs_message_delay_increase = [DELAY_INCREASE; DEFAULT=10 sec]

sqs_cdx_max_messages = [MAX_CDX_MESSAGES_RECEIVED_PER_ITERATION; DEFAULT=10]

cdx_lambda_n_iterations = [NUMBER_ITERATIONS_CDX_FUNCTION=2]

cdx_run_id = [CDX_RUN_METRICS_IDENTIFIER; DEFAULT=1]

```
This file is automatically loaded by terraform and the values are assigned values to the variables in ```main.tf``` and ```provider.tf``` 

NB: The file ```backend.tf``` should be modified directly in the code :
- line 5: provide your AWS bucket name (see [Prerequisites](#prerequisites))
- line 10: change the key with a key of your own, e.g. 'terraform/state/<your-lambda function>/terraform.tfstate' 

## Usage
- [Deploy AWS resources](#deploy-aws-resources)	
- [Fill SQS queue ](#fill-sqs-queue)
- [Test Function](#test-function)
- [Monitor Process](#monitor-process)
- [Collect Results](#collect-results)
- [Clean Up](#clean-up)

### Deploy AWS resources

#### init
The terraform init command is used to initialize a working directory containing Terraform configuration files. This is the first command that should be run after writing a new Terraform configuration or cloning an existing one from version control. It is safe to run this command multiple times.
```
# Go to terraform folder
$ cd terraform

# Initialize terraform
$ terraform init
```

#### plan
The terraform plan command is used to create an execution plan. Terraform performs a refresh, unless explicitly disabled, and then determines what actions are necessary to achieve the desired state specified in the configuration files. The optional -out argument can be used to save the generated plan to a file for later execution with terraform apply, which can be useful when running Terraform in automation.
```
$ terraform plan -out './plan'
```

#### apply
The terraform apply command is used to apply the changes required to reach the desired state of the configuration, or the pre-determined set of actions generated by a terraform plan execution plan.
By using the “plan” command before “apply,” you’ll be aware of any unforeseen errors or unexpected resource creation/modification!
```
$ terraform apply "./plan"
```

### Fill SQS queue
The 'fill_sqs_queue.py' script adds messages to the initial SQS queue.
These messages each contain a set of urls. The lambda function takes messages from the SQS queue and -for the given urls- requests CDX records from the Internet Archive.

Before running the script, set the following environment variable in your cmd prompt:
- 'AWS_PROFILE'=<'AWS profile'>

Execute the script:
```
# Go to cdx folder
$ cd ..

# Fill sqs queue
$ python fill_sqs_queue.py [ARGUMENTS]

Arguments:
  -f  path to the file containing urls 
  -q  SQS ID: human readable name of sqs cdx queue (check the terraform output)

```

### Test Function
Look up your newly create Lambda function in the AWS console (note, make sure that the console is set to the correct region 'eu-central-1').
Open the function and create a test event for your function. You can use the "hello world" event template.
The content of the test event is not used by the python code.
Run you're newly created test event and check the Lambda logs to see the result.	

### Monitor Process
Each AWS service in the workflow can be monitored in the AWS console. 	
The cloudwatch logs provide additional information on the lambda functions.
Set the logging level to 'info' to get verbose information on the progress.	
	
The 'get_cdx_scrape_logs.py' script can be used to query the cloudwatch logs, to retrieve the metrics of the CDX Lambda funtion.
The output of this script is a csv file containing: domain, run id, number of urls fetched from internet archive, number of filtered urls.
Because there is a maximum on the number of results that cloudwatch can return (10.000), the script is currently configured to query the result of 1 single day (24 hours).
The date is hardcoded and should be updated before running the script. The output filename contains the date for which the results were collected.

### Collect Results
Scraping results are collected in your s3 bucket

### Clean up
Run the following [command](https://www.terraform.io/docs/commands/destroy.html), to cleanup the AWS resources that were deployed by terraform:
```
# Go to terraform folder
$ cd terraform

# Clean up AWS resources
$ terraform destroy
```
