#!/bin/bash

cd terraform/
terraform init -reconfigure
terraform plan -out './plan'
terraform apply "./plan"
cd ..
