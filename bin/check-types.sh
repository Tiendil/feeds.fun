#!/usr/bin/bash

set -e

echo "run mypy"

./bin/backend-utils.sh poetry run mypy --show-traceback .

echo "run vue-tsc"

./bin/frontend-utils.sh npm run type-check
