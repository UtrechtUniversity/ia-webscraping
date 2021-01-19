#!/bin/bash

## Lambda example build script ""

# install requirements
pip3 install --target ./example_lambda/ -r ./example_lambda/requirements.txt

# Create zip file
cd example_lambda; zip -r ../example_lambda.zip *
cd ..

# Generate hash of zip file
openssl dgst -sha256 -binary example_lambda.zip | openssl enc -base64 > example_lambda.zip.sha256

# Upload to s3
aws s3 cp example_lambda.zip s3://rjbood-crunchbase-terraform-lambda-example/v1.0.5/example_lambda.zip --profile crunch
