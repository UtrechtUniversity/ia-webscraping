#!/bin/bash

## Lambda cdx build script ""

# install requirements
pip3 install --upgrade --target ./lambda-cdx/ -r ./lambda-cdx/requirements.txt
pip3 install --upgrade --target ./lambda-scrape/ -r ./lambda-scrape/requirements.txt

echo "done installing packages"

# Create zip file
cd lambda-cdx; zip -r ../lambda-cdx.zip *
cd ..
cd lambda-scrape; zip -r ../lambda-scrape.zip *
cd ..

echo "done zipping"

# Generate hash of zip file
openssl dgst -sha256 -binary lambda-cdx.zip | openssl enc -base64 > lambda-cdx.zip.sha256
openssl dgst -sha256 -binary lambda-scrape.zip | openssl enc -base64 > lambda-scrape.zip.sha256

echo "done digesting"

# Upload to s3
aws s3 cp lambda-cdx.zip s3://iascraping/cdx-records/lambda-cdx.zip --profile 'crunch'
aws s3 cp lambda-scrape.zip s3://iascraping/cdx-records/lambda-scrape.zip --profile 'crunch'