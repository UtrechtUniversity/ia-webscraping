#!/bin/bash

## Lambda cdx build script ""
CODE_BUCKET="my-bucket"
LAMBDA_NAME="my-lambda"
AWS_PROFILE="crunch"

# install requirements
pip3 install --upgrade --target ./lambda-cdx/ -r ./lambda-cdx/requirements.txt
pip3 install --upgrade --target ./lambda-scrape/ -r ./lambda-scrape/requirements.txt

echo "done installing packages"

mkdir -p zips

# Create zip file
cd lambda-cdx; zip -r ../zips/${LAMBDA_NAME}-cdx.zip *
cd ..
cd lambda-scrape; zip -r ../zips/${LAMBDA_NAME}-scrape.zip *
cd ..

echo "done zipping"

# Generate hash of zip file
openssl dgst -sha256 -binary ./zips/${LAMBDA_NAME}-cdx.zip | openssl enc -base64 > ./zips/${LAMBDA_NAME}-cdx.zip.sha256
openssl dgst -sha256 -binary ./zips/${LAMBDA_NAME}-scrape.zip | openssl enc -base64 > ./zips/${LAMBDA_NAME}-scrape.zip.sha256

echo "done digesting"

# Upload to s3
aws s3 cp ./zips/${LAMBDA_NAME}-cdx.zip s3://${CODE_BUCKET}/cdx-records/${LAMBDA_NAME}-cdx.zip --profile ${AWS_PROFILE}
aws s3 cp ./zips/${LAMBDA_NAME}-scrape.zip s3://${CODE_BUCKET}/cdx-records/${LAMBDA_NAME}-scrape.zip --profile ${AWS_PROFILE}