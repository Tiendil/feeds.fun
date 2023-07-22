#!/usr/bin/bash

set -e

echo "run mypy"

./bin/backend-utils.sh poetry run mypy .
