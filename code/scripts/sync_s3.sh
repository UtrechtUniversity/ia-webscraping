#!/bin/bash

BUCKET=$1
TARGET_FOLDER=$2
PROFILE="crunch"

if [[ -z "${BUCKET}" ]]; then
  echo "need a bucket"
  exit
fi

if [[ -z "${TARGET_FOLDER}" ]]; then
  echo "need a target folder"
  exit
fi

aws s3 sync ${BUCKET} ${TARGET_FOLDER} --profile ${PROFILE}

echo "done"
