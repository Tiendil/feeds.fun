#!/usr/bin/bash

echo "build base images"

docker compose --profile dev-build build backend-build frontend-build
