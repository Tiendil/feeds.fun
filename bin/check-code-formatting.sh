#!/usr/bin/bash

set -e

./bin/backend-utils.sh poetry run isort --check-only .
./bin/backend-utils.sh poetry run black --check .
