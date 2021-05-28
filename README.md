# ia-webscraping

# Lambda: get CDX records

This project collects -for a given set of inital urls- CDX records from the Internet Archive.
The code in this project is run at AWS.
Terraform is used to deploy the following AWS resources:
- SQS queue 
- Lambda
- CloudWatch
- S3 bucket

## Architecture
The ia-webscraping repository utilizes the following AWS services:
- SQS: to create a queue of scraping tasks, manage the distribution of these tasks among the fetching Lambda functions and give insight in the result of the task.
- AWS Lambda: to run the fetching code without the need for provisioning or managing servers.
- S3: for storage of the HTML pages
- CloudWatch: to monitor the metrics of the SQS queue and Lambda functions
- CloudWatch trigger: to trigger the Lambda function on a timely basis, the interval can be changed to throttle the process

Deploying this solution will result in the following scrape pipeline in the AWS Cloud.

![Alt text](docs/architecture_overview.png?raw=true "Architecture Overview")


## Getting started

  - [Prerequisites](#prerequisites)
  - [Copy the Project](#copy-the-project)
  - [Build Lambda function](#build-lambda-function)
  - [Update Scripts](#update-terraform-scripts)

### Prerequisites
To install and run this project you need to have the following prerequisites installed:
- (optional) install package manager. 
	- windows: [chocolatey](https://chocolatey.org/install), 
	- mac: [brew](https://brew.sh)
	- With a package manager it becomes easy to install/update the below prerequisites. 
    For example:  ```choco install awscli' ```
- [install aws cli](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)
- [configure aws cli credentials](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)
    create a profile with the name 'crunch' 
- install python3 
- install pip3
- install [terraform](https://www.terraform.io/downloads.html)
- create a personal S3 bucket in AWS (region: eu-central-1)

### Copy the Project

Create your own copy of the 'cdx-records' directory on your local client.

### Build lambda functions

The 'build.sh' script will for each of the lambda functions:
- install all requirements from the 'requirements.txt' file in the lambda folder
- create a zip file 
- calculate a hash of this zipfile and write this to 'example_lambda.zip.sha256'
- upload the zip file to the s3 bucket

# First update the build script: 
- line 16: provide your AWS bucket name (see [Prerequisites](#prerequisites))

# Then run the build script
```
# Go to terraform folder
$ cd cdx-records

# Build zip files
$ ./build.sh 
```

### Update Terraform Scripts

In the [terraform folder](/terraform) create a file ```terraform.tfvars``` that lists terraform variables and the corresponding values:

```
bucket_name = [YOUR_BUCKET_NAME]

lambda_name = [YOUR_LAMBDA_NAME]

```
This file is automatically loaded by terraform and the values are assigned values to the variables in ```main.tf``` and ```provider.tf``` 

NB: The file ```backend.tf``` should be modified directly in the code :
- line 5: provide your AWS bucket name (see [Prerequisites](#prerequisites))
- line 10: change the key with a key of your own, e.g. 'terraform/state/<your-lambda function>/terraform.tfstate' 


## Run
- [Deploy AWS resources](#deploy-aws-resources)
- [Fill SQS queue ](#fill-sqs-queue)
- [Test Function](#test-function)
- [Clean Up](#clean-up)

