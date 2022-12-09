#!/bin/bash

VARS_FILE=./.vars

CODE_BUCKET="my-code-bucket"
RESULT_BUCKET="my-result-bucket"
LAMBDA_NAME="my-lambda"
AWS_PROFILE="crunch"
FORMATS_TO_SAVE="txt,links"
START_YEAR="2018"
END_YEAR="2022"
MATCH_EXACT_URL="0"
URL_LIMIT_PER_DOMAIN="1000"

function get_var_value {
  while read -r line; do
    if [[ ${line} == *${2}* ]]; then
      echo ${line##* }
    fi
  done < ${1}
}

if [[ -f "${VARS_FILE}" ]]; then
  CODE_BUCKET=$(get_var_value ${VARS_FILE} "CODE_BUCKET")
  RESULT_BUCKET=$(get_var_value ${VARS_FILE} "RESULT_BUCKET")
  LAMBDA_NAME=$(get_var_value ${VARS_FILE} "LAMBDA_NAME")
  AWS_PROFILE=$(get_var_value ${VARS_FILE} "AWS_PROFILE")
  FORMATS_TO_SAVE=$(get_var_value ${VARS_FILE} "FORMATS_TO_SAVE")
  START_YEAR=$(get_var_value ${VARS_FILE} "START_YEAR")
  END_YEAR=$(get_var_value ${VARS_FILE} "END_YEAR")
  MATCH_EXACT_URL=$(get_var_value ${VARS_FILE} "MATCH_EXACT_URL")
  URL_LIMIT_PER_DOMAIN=$(get_var_value ${VARS_FILE} "URL_LIMIT_PER_DOMAIN")
fi

# arguments:
# -c <code bucket name>
# -r <result bucket name>
# -l <lambda prefix>
# -a <AWS profile>
# -s <start year>
# -e <end year>
# -f <formats to save>
# -x <limit of scraped pages per provided URL; 0 for unlimited>
# -m (switch for exact URL match)
# -n (skips re-install of third party packages)
# -h (shows help)

# example:
# ./build.sh -c prod-crunchbase-code -r prod-crunchbase-results -l prod-lambda -a crunch -s 2018 -e 2022 -x 3000 -n
HELP=0
NOINSTALL=0
while getopts "c:r:l:a:s:e:f:x:mhn" opt; do
  case $opt in
    c)
      USER_CODE_BUCKET=$OPTARG
      ;;
    r)
      USER_RESULT_BUCKET=$OPTARG
      ;;
    l)
      USER_LAMBDA_NAME=$OPTARG
      ;;
    a)
      USER_AWS_PROFILE=$OPTARG
      ;;
    s)
      USER_START_YEAR=$OPTARG
      ;;
    e)
      USER_END_YEAR=$OPTARG
      ;;
    f)
      USER_FORMATS_TO_SAVE=$OPTARG
      ;;
    x)
      USER_URL_LIMIT_PER_DOMAIN=$OPTARG
      ;;
    m)
      USER_MATCH_EXACT_URL="1"
      ;;
    h)
      HELP=1
      ;;
    n)
      NOINSTALL=1
      ;;
  esac
done

if [[ "$HELP" == "1" ]]; then
	echo "Arguments:"
	echo "-c <code bucket name>"
	echo "-r <result bucket name>"
	echo "-l <lambda prefix>"
	echo "-a <AWS profile>"
	echo "-s <start year>"
	echo "-e <end year>"
	echo "-x <limit of scraped pages per provided URL; 0 for unlimited>"
	echo "-m (match exact URL only; ignores presence of 'www')"
	echo "-f <formats to save; html, txt and/or links; separate by comma>"
	echo "-n (skip re-install of packages)"
	echo
	echo "Usage example:"
	echo './build.sh -c prod-crunchbase-code -r prod-crunchbase-results -l prod-lambda -f "txt,links"'
	exit
fi

if  [[ ! -z "$USER_CODE_BUCKET" ]]; then
	CODE_BUCKET=$USER_CODE_BUCKET
fi

if  [[ ! -z "$USER_RESULT_BUCKET" ]]; then
	RESULT_BUCKET=$USER_RESULT_BUCKET
fi

if  [[ ! -z "$USER_LAMBDA_NAME" ]]; then
	LAMBDA_NAME=$USER_LAMBDA_NAME
fi

if  [[ ! -z "$USER_AWS_PROFILE" ]]; then
	AWS_PROFILE=$USER_AWS_PROFILE
fi

if  [[ ! -z "$USER_START_YEAR" ]]; then
	START_YEAR=$USER_START_YEAR
fi

if  [[ ! -z "$USER_END_YEAR" ]]; then
	END_YEAR=$USER_END_YEAR
fi

if  [[ ! -z "$USER_URL_LIMIT_PER_DOMAIN" ]]; then
	URL_LIMIT_PER_DOMAIN=$USER_URL_LIMIT_PER_DOMAIN
fi

if  [[ ! -z "$USER_FORMATS_TO_SAVE" ]]; then
	FORMATS_TO_SAVE=$USER_FORMATS_TO_SAVE
fi

if  [[ ! -z "$USER_MATCH_EXACT_URL" ]]; then
	MATCH_EXACT_URL=$USER_MATCH_EXACT_URL
fi


echo ""
echo "CURRENT SETTINGS"
echo '(run "./build.sh -h" for help)'
echo "code bucket:     $CODE_BUCKET"
echo "result bucket:   $RESULT_BUCKET"
echo "lambda prefix:   $LAMBDA_NAME"
echo "AWS profile:     $AWS_PROFILE"
echo "formats:         $FORMATS_TO_SAVE"
echo "start year:      $START_YEAR"
echo "end year:        $END_YEAR"
echo "URL limit:       $URL_LIMIT_PER_DOMAIN"
echo "match exact URL: $MATCH_EXACT_URL"
echo
read -p "proceed [y/n]: " PROCEED

if [[ "$PROCEED" != "y"  && "$PROCEED" != "Y" ]]; then
	echo "exiting"
	exit
fi

# save settings
echo "" > ${VARS_FILE}
echo "CODE_BUCKET ${CODE_BUCKET}" >> ${VARS_FILE}
echo "RESULT_BUCKET ${RESULT_BUCKET}" >> ${VARS_FILE}
echo "LAMBDA_NAME ${LAMBDA_NAME}" >> ${VARS_FILE}
echo "AWS_PROFILE ${AWS_PROFILE}" >> ${VARS_FILE}
echo "FORMATS_TO_SAVE ${FORMATS_TO_SAVE}" >> ${VARS_FILE}
echo "START_YEAR ${START_YEAR}" >> ${VARS_FILE}
echo "END_YEAR ${END_YEAR}" >> ${VARS_FILE}
echo "MATCH_EXACT_URL ${MATCH_EXACT_URL}">> ${VARS_FILE}
echo "URL_LIMIT_PER_DOMAIN ${URL_LIMIT_PER_DOMAIN}">> ${VARS_FILE}

# non-changeable vars
CUSTOM_LOG_GROUP="metrics"
CUSTOM_LOG_STREAM_CDX="cdx_metrics"
CUSTOM_LOG_STREAM_SCRAPE="scrape_metrics"

# make no changes below this line
TF_VARS_TPL=./templates/terraform.tfvars.template
TF_VARS_FILE=./terraform/terraform.tfvars
TF_BACKEND_TPL=./templates/backend.tf.template
TF_BACKEND_FILE=./terraform/backend.tf
TF_PROVIDER_TPL=./templates/provider.tf.template
TF_PROVIDER_FILE=./terraform/provider.tf
PY_FILL_QUEUE_TPL=./templates/fill_sqs_queue.py.template
PY_FILL_QUEUE_FILE=./fill_sqs_queue.py

if [ -e $TF_VARS_FILE ]
then
	rm $TF_VARS_FILE
fi

if [ -e $TF_BACKEND_FILE ]
then
	rm $TF_BACKEND_FILE
fi

if [ -e $TF_PROVIDER_FILE ]
then
	rm $TF_PROVIDER_FILE
fi

if [ -e $PY_FILL_QUEUE_FILE ]
then
	rm $PY_FILL_QUEUE_FILE
fi

# configure Terraform vars file
cp $TF_VARS_TPL $TF_VARS_FILE
sed -i "s/\[CODE_BUCKET\]/${CODE_BUCKET}/g" $TF_VARS_FILE
sed -i "s/\[RESULT_BUCKET\]/${RESULT_BUCKET}/g" $TF_VARS_FILE
sed -i "s/\[LAMBDA_NAME\]/${LAMBDA_NAME}/g" $TF_VARS_FILE
sed -i "s/\[FORMATS_TO_SAVE\]/${FORMATS_TO_SAVE}/g" $TF_VARS_FILE
sed -i "s/\[START_YEAR\]/${START_YEAR}/g" $TF_VARS_FILE
sed -i "s/\[END_YEAR\]/${END_YEAR}/g" $TF_VARS_FILE
sed -i "s/\[URL_LIMIT_PER_DOMAIN\]/${URL_LIMIT_PER_DOMAIN}/g" $TF_VARS_FILE
sed -i "s/\[MATCH_EXACT_URL\]/${MATCH_EXACT_URL}/g" $TF_VARS_FILE
sed -i "s/\[CUSTOM_LOG_GROUP\]/${CUSTOM_LOG_GROUP}/g" $TF_VARS_FILE
sed -i "s/\[CUSTOM_LOG_STREAM_CDX\]/${CUSTOM_LOG_STREAM_CDX}/g" $TF_VARS_FILE
sed -i "s/\[CUSTOM_LOG_STREAM_SCRAPE\]/${CUSTOM_LOG_STREAM_SCRAPE}/g" $TF_VARS_FILE

echo "Copied template to ${TF_VARS_FILE}"

# configure Terraform backend config
cp $TF_BACKEND_TPL $TF_BACKEND_FILE
sed -i "s/\[CODE_BUCKET\]/${CODE_BUCKET}/g" $TF_BACKEND_FILE
sed -i "s/\[LAMBDA_NAME\]/${LAMBDA_NAME}/g" $TF_BACKEND_FILE
sed -i "s/\[AWS_PROFILE\]/${AWS_PROFILE}/g" $TF_BACKEND_FILE

echo "Copied template to ${TF_BACKEND_FILE}"

# configure Terraform provider config
cp $TF_PROVIDER_TPL $TF_PROVIDER_FILE
sed -i "s/\[AWS_PROFILE\]/${AWS_PROFILE}/g" $TF_PROVIDER_FILE

echo "Copied template to ${TF_PROVIDER_FILE}"

# configure job queue script
cp $PY_FILL_QUEUE_TPL $PY_FILL_QUEUE_FILE
sed -i "s/\[SQS_QUEUE_NAME\]/${LAMBDA_NAME}-cdx-queue/g" $PY_FILL_QUEUE_FILE
sed -i "s/\[AWS_PROFILE\]/${AWS_PROFILE}/g" $PY_FILL_QUEUE_FILE
sed -i "s/\[SQS_MESSAGE_AUTHOR\]/${LAMBDA_NAME}/g" $PY_FILL_QUEUE_FILE

echo "Copied template to ${PY_FILL_QUEUE_FILE}"

# checking existence of code bucket (which needs to exist)
BUCKET_LS=$(aws s3 ls s3://${CODE_BUCKET} --profile ${AWS_PROFILE} 2>&1)

if [[ "$BUCKET_LS" =~ .*"bucket does not exist"*. ]]; then
	echo "The specified bucket '${CODE_BUCKET}' does not exist. Create it and try again."
	exit
fi

# optional skipping of installing necessary packages (for repeated builds)
if [[ "$NOINSTALL" == "1" ]]; then
	echo "Skipping requirements install"
else
	# install requirements
	pip3 install --upgrade --target ./lambda-cdx/ -r ./lambda-cdx/requirements.txt
	pip3 install --upgrade --target ./lambda-scrape/ -r ./lambda-scrape/requirements.txt
	echo "Done installing packages"
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
