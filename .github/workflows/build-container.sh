#!/usr/bin/env bash

docker build -t $IMAGE_NAME .
docker push $IMAGE_NAME
