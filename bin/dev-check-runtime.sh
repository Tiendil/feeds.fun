#!/usr/bin/bash

set -e

CONTAINER="ffun-backend:check-ffun-runnable-in-prod"

echo "build backend container"

docker build -t $CONTAINER -f ./docker/prod/backend/Dockerfile .

echo "run checks"

echo "check that CLI works"
docker run --rm $CONTAINER ffun --help

echo "check that CLI shows configs and not import any dev dependencies in process"
docker run --rm $CONTAINER ffun print-configs
