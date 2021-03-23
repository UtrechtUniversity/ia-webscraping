#!/bin/bash

## Lambda cdx build script ""

# install requirements
pip3 install --upgrade --target ./lambda-cdx-crunchbase-dev-mvos/ -r ./lambda-cdx-crunchbase-dev-mvos/requirements.txt
pip3 install --upgrade --target ./lambda-scraper-dev-csk/ -r ./lambda-scraper-dev-csk/requirements.txt

echo "done installing packages"

# Create zip file
cd lambda-cdx-crunchbase-dev-mvos; zip -r ../lambda-cdx-crunchbase-dev-mvos.zip *
cd ..
cd lambda-scraper-dev-csk; zip -r ../lambda-scraper-dev-csk.zip *
cd ..

echo "done zipping"

# Generate hash of zip file
openssl dgst -sha256 -binary lambda-cdx-crunchbase-dev-mvos.zip | openssl enc -base64 > lambda-cdx-crunchbase-dev-mvos.zip.sha256
openssl dgst -sha256 -binary lambda-scraper-dev-csk.zip | openssl enc -base64 > lambda-scraper-dev-csk.zip.sha256

echo "done digesting"

# Upload to s3
aws s3 cp lambda-cdx-crunchbase-dev-mvos.zip s3://crunchbase-dev-mvos-source/cdx-records/lambda-cdx-crunchbase-dev-mvos.zip --profile 'crunch'
aws s3 cp lambda-scraper-dev-csk.zip s3://crunchbase-dev-mvos-source/cdx-records/lambda-scraper-dev-csk.zip --profile 'crunch'