#!/bin/bash

INSTALL=0

while getopts "i" opt; do
  case $opt in
    i)
      INSTALL=1
      ;;
  esac
done


TF_BACKEND_FILE=./terraform/backend.tf
CONTENTS=$(cat $TF_BACKEND_FILE)

extract() {
  echo $(echo $CONTENTS | grep -o "$1[[:blank:]]\?=[[:blank:]]\?\"[A-Za-z\-]*\"" | sed -e 's/^[^"]*"//' | sed -e 's/"//')
}

CODE_BUCKET=$(extract "bucket")
AWS_PROFILE=$(extract "profile")
LAMBDA_NAME=$(echo $CONTENTS | grep -o "key[[:blank:]]\?=[[:blank:]]\?\"[A-Za-z\.\/]*\"" | sed -e 's/key = "terraform\/state\///' | sed -e 's/\/terraform\.tfstate"//')

#echo $CODE_BUCKET
#echo $AWS_PROFILE
#echo $LAMBDA_NAME

# optional skipping of installing necessary packages (for repeated builds)
if [[ "$INSTALL" == "1" ]]; then

	# install requirements
	pip3 install --upgrade --target ./lambda-cdx/ -r ./lambda-cdx/requirements.txt
	pip3 install --upgrade --target ./lambda-scrape/ -r ./lambda-scrape/requirements.txt

	echo "Done installing packages"

else

	echo "Skipping requirements install"

fi

# Create zip files
mkdir -p zips

rm -f ./zips/${LAMBDA_NAME}-cdx.zip
cd lambda-cdx; zip -r ../zips/${LAMBDA_NAME}-cdx.zip *; cd ..
rm -f ./zips/${LAMBDA_NAME}-scrape.zip
cd lambda-scrape; zip -r ../zips/${LAMBDA_NAME}-scrape.zip *; cd ..

echo "Done zipping"


# Generate hash of zip files
# TODO: these were not uploaded originally; they are now, but no checks are performed.
rm -f ./zips/${LAMBDA_NAME}-cdx.zip.sha256
openssl dgst -sha256 -binary ./zips/${LAMBDA_NAME}-cdx.zip | openssl enc -base64 > ./zips/${LAMBDA_NAME}-cdx.zip.sha256
rm -f ./zips/${LAMBDA_NAME}-scrape.zip.sha256
openssl dgst -sha256 -binary ./zips/${LAMBDA_NAME}-scrape.zip | openssl enc -base64 > ./zips/${LAMBDA_NAME}-scrape.zip.sha256

echo "Done digesting"

# Upload to s3
aws s3 sync ./zips/ s3://${CODE_BUCKET}/code/ --profile ${AWS_PROFILE} --exclude "*" --include "${LAMBDA_NAME}*.*"

echo "Done uploading"

#cd terraform/
#terraform plan -out './plan'
#terraform apply "./plan"
#cd ..
