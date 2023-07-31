#!/usr/bin/bash

set -e

# TODO: remove
VERSION="0.2.2"

docker build \
       --network=host \
       --build-arg VERSION="$VERSION" \
       -t feeds-fun-backend:latest \
       -t feeds-fun-backend:$VERSION \
       ./docker/backend-prod/
