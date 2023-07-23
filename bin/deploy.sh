#!/usr/bin/env bash
set -euo pipefail

curl -L https://github.com/bep/s3deploy/releases/download/v2.5.1/s3deploy_2.5.1_Linux-64bit.tar.gz -o bin/s3deploy.tar.gz
mkdir -p bin/s3deploy
tar -xf bin/s3deploy.tar.gz -C bin/s3deploy
rm bin/s3deploy.tar.gz

bin/s3deploy/s3deploy \
  -bucket $AWS_S3_BUCKET -key $AWS_ACCESS_KEY_ID -secret $AWS_SECRET_ACCESS_KEY \
  -region eu-west-1 -config .s3deploy.yml -source dist -path v1/nthp-api-master
