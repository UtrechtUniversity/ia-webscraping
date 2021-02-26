#!/bin/bash

## Lambda cdx build script ""

# install requirements
pip3 install --target ./lambda-cdx-crunchbase-dev-mvos/ -r ./lambda-cdx-crunchbase-dev-mvos/requirements.txt

# Create zip file
cd lambda-cdx-crunchbase-dev-mvos; zip -r ../lambda-cdx-crunchbase-dev-mvos.zip *
cd ..

# Generate hash of zip file
openssl dgst -sha256 -binary lambda-cdx-crunchbase-dev-mvos.zip | openssl enc -base64 > lambda-cdx-crunchbase-dev-mvos.zip.sha256

# Upload to s3
aws s3 cp lambda-cdx-crunchbase-dev-mvos.zip s3://crunchbase-dev-mvos-source/cdx-records/lambda-cdx-crunchbase-dev-mvos.zip --profile 'default'