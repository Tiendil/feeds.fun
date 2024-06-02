#!/usr/bin/bash

set -e

echo "run autoflake"

./bin/backend-utils.sh poetry run autoflake --check --quiet .

echo "run flake8"

./bin/backend-utils.sh poetry run flake8 .

echo "run mypy"

./bin/backend-utils.sh poetry run mypy --show-traceback .

echo "run vue-tsc"

./bin/frontend-utils.sh npm run type-check
