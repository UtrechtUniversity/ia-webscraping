# AWS AMI for the Crunchbase project

This module contains the scripts and configuration to build a custom AMI for the Crunchbase project.
The AMI is build with the command line tool: Packer. In the custom AMI all required software (e.g. R, Rstudio, R packages) can be installed that are required for the crunchbase project.

## Why build a custom AMI
Installing R and R packages can take a considerable amount of time during the bootstrap of the EC2 server (total bootstrap: 15 minutes).
By building a custom AMI, all the packages can be installed in a seperate step. 
This makes the deployment of the Rstudio server with Terraform considerable shorter (i.e. couple of minutes).

## Prerequisites

### Install Packer

[Packer](https://learn.hashicorp.com/packer) is the command line tool that's used by this module to build a custom AWS AMI. 
To build the image, the packer cmd tool must be installed on your local machine.
For more install information, [how to install packer](https://learn.hashicorp.com/tutorials/packer/getting-started-install)

### AWS credentials setup
Before building a new crunch AMI, the AWS credentials must be configured to allow for programmatic access
- configure AWS credentials
    - create AWS profile (e.g. crunch)
- set profile name (2 options)
    - update profile name in packer config file (i.e. ami-crunch.pkr.hcl)
    - set profile environment variable (e.g. 'export AWS_PROFILE=crunch')


## Validate and Build

Before building the crunch AMI, the packer config file should be validated.
To validate, run the following command.

```sh
    packer validate ./config/ami-crunch.pkr.hcl
```

If the validation step has succeeded, run the following command to build the ami.

```sh
    packer build ./config/ami-automl.pkr.hcl
```