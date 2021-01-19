# Lambda Example

This project deploys a basic Python AWS Lambda function & SQS queue to AWS.
The function deployment package (i.e zip file) is build with the 'build.sh' script.
A Terraform script is used to deploy the AWS resources.
And there is a 'fill_sqs_queue' script to send an SQS message to the newly created queue.

## Deployment

This section describes the steps that are required to build, deploy, test, destroy the Lambda example.

### Prerequisites 

Before deploying this Lambda example, the following required resources need to be setup:
- (optional) install package manager (windows: [chocolatey](https://chocolatey.org/install), mac: [brew](https://brew.sh))
    With a package manager it becomes easy to install/update the below prerequisites (e.g. installing [awscli](https://chocolatey.org/packages/awscli) with 'choco', 'choco install awscli').
- install aws cli (see [link](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html))
- configure aws cli credentials (see [link](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html))
    create a profile and remember the name of this profile (if no name was specified, the name of the profile is 'default')
- install python3 
- install [terraform](https://www.terraform.io/downloads.html)
- create a personal S3 bucket in AWS (region: eu-central-1)

### Copy the Project

Create your own copy of the 'Lambda_Example' directory on your local client.

### Change build.sh parameters

Change the following lines in the 'build.sh' script
- line 16: change the bucket name 'rjbood-crunchbase-terraform-lambda-example' with the bucket name that you created in the Prerequisites
- line 16: change the profile name 'crunch' with the name of your AWS profile (i.e. 'default', see Prerequisites)

### Build Lambda function

The 'build.sh' script will:
- install all requirements from the 'requirements.txt' file in the 'example_lambda folder'
- create a zip file 'example_lambda.zip'
- calculate a hash of this zipfile and write this to 'example_lambda.zip.sha256'
- upload the 'example_lambda.zip' file to the s3 bucket

Execute the 'build.sh' script from the command line
'''
    Lambda_Example_copy> ./build.sh
'''

### Update Terraform scripts

The Terraform deployment consist of 4 terraform scripts:
- backend.tf
- provider.tf
- main.tf
- output.tf

#### backend.tf
In the backend.tf we configure where Terraform stores the state file of the created resources. By default, when you run Terraform in the folder /foo/bar, Terraform creates the file /foo/bar/terraform.tfstate. But in this example we store the state in a S3 bucket. With this state file, Terraform is able to find the resources it created previously and update them accordingly.
Since this is a copy of the original project, we need to update the backend.tf file with the s3 location to store the state of this new project.

Update the following parameters in the backend.tf file:
- line 5: change the 'terraform-crunchbase-surf-frankfurt' with your own bucket name that you created in the Prerequisites
- line 7: change the profile name 'crunch' with the name of your AWS profile (i.e. 'default', see Prerequisites)
- line 10: change the key 'terraform/state/crunchbase_rjbood_lambda_example/terraform.tfstate' with a key of your own.

#### provider.tf
Terraform relies on plugins called "providers" to interact with remote systems like AWS. 
The provider.tf file contains the configuration of the providers that Terraform requires to install and deploy the resources of the Terraform deployment.

Update the following paramters in the provider.tf file:
- line 4: change the profile name 'crunch' with the name of your AWS profile (i.e. 'default', see Prerequisites)

#### main.tf
In the main.tf the resources are specified that we want to deploy to AWS and with the required settings (note, settings not specified will fall back to the default value of AWS).
The following resources are defined:
- [aws_iam_role](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role): the IAM role required for the Lambda function
- [aws_iam_role_policy_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy_attachment): the AWS managed policy that gives the permissions that the Lambda function requires
- [aws_sqs_queue](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy_attachment): the SQS queue
- [aws_lambda_function](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_function): Lambda function

In addition, we specifiy a data object 'aws_s3_bucket_object'. This data object is used in the deployment to point terraform to the 'example_lambda.zip' file, uploaded by 'build.sh' script'.

Update the following parameters in the main.tf file:
- line 7: change the name 'lambda_example_rjbood' with a name of your own (i.e. lambda_example_improved)
- line 27: change the bucket name 'rjbood-crunchbase-terraform-lambda-example' with the bucket name where you uploaded the 'example_lambda.zip' file (e.g. bucket name from 'build.sh' script)
- line 32: update the sqs queue name 'terraform-example-queue-rjbood' with a name of your own (i.e. lambda_example_sqs_improved)
- line 40: update the function name 'lambda_example_rjbood' with a function name of your own (i.e. 'lambda_example_improved')
- (optional)line 50: make sure the path specified points to the 'example_lambda.zip.sha256' file created by the 'build.sh' script

#### output.tf
The output.tf file defines the parameters that need to be available as output parametes.
In this example, the SQS ID and ARN are available as output parameters.
Use the SQS ID in the 'fill_sqs_queue.py' script.

### Run Terraform script

#### init
The terraform init command is used to initialize a working directory containing Terraform configuration files. This is the first command that should be run after writing a new Terraform configuration or cloning an existing one from version control. It is safe to run this command multiple times.
'''
    terraform init
'''

#### plan
The terraform plan command is used to create an execution plan. Terraform performs a refresh, unless explicitly disabled, and then determines what actions are necessary to achieve the desired state specified in the configuration files. The optional -out argument can be used to save the generated plan to a file for later execution with terraform apply, which can be useful when running Terraform in automation.
'''
    terraform plan -out './plan'
'''

#### apply
The terraform apply command is used to apply the changes required to reach the desired state of the configuration, or the pre-determined set of actions generated by a terraform plan execution plan.
''''
    terraform apply "./plan"
''''

### Fill SQS queue
The 'fill_sqs_queue.py' script creates a single SQS message in the SQS queue.

Before running the script, update the SQS queue that is hardcoded in the python code:
line 7: change the 'https://sqs.eu-central-1.amazonaws.com/080708105962/terraform-example-queue-rjbood' sqs ID in to the SQS ID that was created by 'terraform apply' command (check the terraform output)

### Test Function
Look up your newly create Lambda function in the AWS console (note, make sure that the console is set to the correct region 'eu-central-1').
Open the function and create a test event for your function. You can use the "hello world" event template.
The content of the test event is not used by the python code.
Run you're newly created test event and check the Lambda logs to see the result.

### Clean up
Run the following [command](https://www.terraform.io/docs/commands/destroy.html), to cleanup the AWS resources that were deployed by terraform:
'''
    terraform destroy
'''