#!/usr/bin/bash

set -e

echo "run isort"

./bin/backend-utils.sh poetry run isort --check-only .

echo "run black"

./bin/backend-utils.sh poetry run black --check .
