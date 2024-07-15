#!/usr/bin/env bash

# shellcheck disable=SC2006
ROOT_DIR=$(dirname $0)
ROOT_DIR=$(cd ${ROOT_DIR} && pwd)
echo "ROOT_DIR=${ROOT_DIR}"
#export PATH=$PATH:${ROOT_DIR}/.github/workflows/bin/ffmpeg/
echo "the PATH is [ ${PATH} ]"

ffmpeg -version

echo $HOME

python ${ROOT_DIR}/config_aws.py $HOME/.aws

ls -la $HOME/.aws/*

cat $HOME/.aws/config

echo $PATH
which ffprobe
which ffmpeg
# todo restore this or it'll never work again!
# python ${ROOT_DIR}/main.py
