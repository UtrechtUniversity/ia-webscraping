
# EC2 instance with Rstudio

This project deploys a EC2 instance and install R studio.
A R studio user is created and an ip-whitelist is added to only give access to preconfigured IP's.

Note, after successful deployment your deployment will cost money. Depending on the instance type the hourly rate differs, the more cpu/memory the more expensive.
Make sure to destroy your resources if you are not using them, this will reduce the cost. Any intermediate results can be saved to S3 before destroying the deployment and downloaded on the new instance when continuing the analyses.

The following R packages are pre-installed:
- devtools
- ggplot2
- itertools
- tm
- wordcloud
- doParallel
- psych
- reshape
- topicmodels
- aws.s3
- aws.ec2metadata

## Deployment

This section describes the steps that are required to deploy, login, destroy the R studio EC2 server.

### Prerequisites 

Before deploying this RStudioServer, the following required resources need to be setup:
note: when installing software on windows, make sure to start a cmd prompt with admin permissions.
- (optional) install package manager (windows: [chocolatey](https://chocolatey.org/install), mac: [brew](https://brew.sh))
    With a package manager it becomes easy to install/update the below prerequisites (e.g. installing [awscli](https://chocolatey.org/packages/awscli) with 'choco', 'choco install awscli').
- install aws cli (see [link](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html))
Windows
```sh
    choco install awscli
```
Mac
```sh
    brew install awscli
```
- configure aws cli credentials (see [link](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html))
    create a 'crunch' profile, with the following command:
```sh
    aws configure --profile crunch
```
- install [terraform](https://www.terraform.io/downloads.html)
Windows
```sh
    choco install terraform
```
Mac
```sh
    brew install terraform
```

### Run Terraform script

### Copy the Project

Create your own copy of the 'RStudioServer' directory on your local client.

### Change build.sh parameters

Create a 'terraform.tfvars' file with the following 7 variables and the value.
- line 1: deployment_name > The name of your deployment; all resources will be tagged with this name (e.g. deployment_name="example-deployment")
- line 2: deployment_owner > Your email address; this will indicate that the AWS resources are owned by you (e.g. deployment_name="test@example.com")
- line 3: ip_whitelist > The IP address or list of addresses that should be granted access to Rstudio. The value should be a list of CIDR ranges, a CIDR range is the ip address of your laptop followed by '/32' (note, use the 'curl http://checkip.amazonaws.com' command in a command prompt to determine the IP address of your Windows laptop. You could also lookup this 'http://checkip.amazonaws.com' url in your browser.) (e.g. ip_whitelist=["192.0.2.0/32"])
- line 4: s3_buckets > The list of S3 bucket ARN(s) that the rstudio server needs to access (ARN = amazon resource name; can be found by looking up the s3 buckets in the AWS console>s3). Note, to give access to the full s3 bucket the bucket ARN must be specified and the bucket ARN followed by '/\*' to give access to all objects in that bucket
(e.g. s3_buckets=["arn:aws:s3:::crunchbase-dev-rjbood", "arn:aws:s3:::crunchbase-dev-rjbood/*"]).  Alternatively, you could only grant access to a folder
(e.g. s3_buckets=["arn:aws:s3:::crunchbase-dev-rjbood/data", "arn:aws:s3:::crunchbase-dev-rjbood/data/*"]).
- line 5: instance_type > the [instance type](https://aws.amazon.com/ec2/instance-types/) of your server; this describe how much CPU cores/memory the server gets. (e.g. instance_type="t3.large"). IMPORTANT, a larger instance type (i.e. more cpu and/or memory) is also more expensive. For test deployments, use t3.large (2 cpu cores, 8 GiB memory). For analysis deployments where more cpu cores are required, use 'm5.2xlarge' (8 cpu cores, 32 GiB memory) or 'm5.xlarge' (4 cpu cores, 16 GiB memory).
- line 6: rstudio_user > the username which will be used to login in RStudio (e.g. rstudio_user="exampleuser")
- line 7: rstudio_user_pwd > the PWD of the R studio user (e.g. rstudio_user_pwd="ex@mple!")

#### provider.tf
Terraform relies on plugins called "providers" to interact with remote systems like AWS. 
The provider.tf file contains the configuration of the providers that Terraform requires to install and deploy the resources of the Terraform deployment.

#### INIT
The terraform init command is used to initialize a working directory containing Terraform configuration files. This is the first command that should be run after writing a new Terraform configuration or cloning an existing one from version control. It's safe to run this command multiple times. 
``` sh
    ./RStudioServer> terraform init
```

#### PLAN
The terraform plan command is used to create an execution plan. Terraform performs a refresh, unless explicitly disabled, and then determines what actions are necessary to achieve the desired state specified in the configuration files. The optional -out argument can be used to save the generated plan to a file for later execution with terraform apply, which can be useful when running Terraform in automation.
``` sh
    ./RStudioServer> terraform plan -out './plan'
```

#### APPLY
The terraform apply command is used to apply the changes required to reach the desired state of the configuration, or the pre-determined set of actions generated by a terraform plan execution plan.
``` sh
    ./RStudioServer> terraform apply "./plan"
```

#### Login to Rstudio
After a successfull deployment, Terraform will print the output. Here you will find the DNS address of your R studio deployment (note, only IP addresses that are whitelisted can access this DNS)
Note, after a successfull terraform deployment, it will take between 10-15 minutes before Rstudio and all R packages are installed.

Example output:
``` sh
    Apply complete! Resources: 7 added, 0 changed, 0 destroyed.

    The state of your infrastructure has been saved to the path
    below. This state is required to modify and destroy your
    infrastructure, so keep it safe. To inspect the complete state
    use the `terraform show` command.

    State path: terraform.tfstate

    Outputs:

    rstudio_public_dns = http://ec2-18-156-118-61.eu-central-1.compute.amazonaws.com:8787
```

### Clean up
Run the following [command](https://www.terraform.io/docs/commands/destroy.html), to cleanup the AWS resources that were deployed by terraform:
``` sh
    ./RStudioServer> terraform destroy
```

## Read/Write data to/from S3 in R

See below for an example of how to read and write data from AWS S3 in R.

``` R
library(aws.s3) # Load S3 library
library(aws.ec2metadata) # Load EC2 metadata library to use credentials from EC2 server for S3 access

# Load data from S3 (bucket='crunchbase-dev-rjbood', key='Crunchbase_test_sample.csv')
path <- 's3://crunchbase-dev-rjbood/Crunchbase_test_sample.csv'
data <- aws.s3::s3read_using(read.csv, object = path, fileEncoding="latin1")

# Write data back to S3 (bucket='crunchbase-dev-rjbood', key='Crunchbase_write_sample.csv')
aws.s3::s3write_using(data, write.csv, object = 's3://crunchbase-dev-rjbood/Crunchbase_write_sample.csv')
```