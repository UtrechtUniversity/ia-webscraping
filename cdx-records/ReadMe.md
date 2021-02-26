# Lambda: get CDX records

This project collects for a given set of inital urls CDX records from the Internet Archive.
The code in this project is run at AWS.
Terraform is used to deploy the following AWS resources:
- SQS queue 
- Lambda
- CloudWatch
- S3 bucket


## Getting started

  - [Prerequisites](#prerequisites)
  - [Copy the Project](#copy-the-project)
  - [Build Lambda function](#build-lambda-function)
  - [Update Scripts](#update-scripts)

### Prerequisites
To install and run this project you need to have the following prerequisites installed:
- (optional) install package manager. 
	- windows: [chocolatey](https://chocolatey.org/install), 
	- mac: [brew](https://brew.sh)
	- With a package manager it becomes easy to install/update the below prerequisites. 
    For example:  ```choco install awscli' ```
- [install aws cli](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)
- [configure aws cli credentials](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)
    create a profile and remember the name of this profile (if no name was specified, the name of the profile is 'default')
- install python3 
- install pip3
- install [terraform](https://www.terraform.io/downloads.html)
- create a personal S3 bucket in AWS (region: eu-central-1)

### Copy the Project

Create your own copy of the 'cdx-records' directory on your local client.

### Update Scripts

Update the following parameters in the [terraform files](/terraform):
- bla  


## Run
- Build and upload lambda function
- Deploy AWS resources
- Fill the first SQS queue with initial messages


