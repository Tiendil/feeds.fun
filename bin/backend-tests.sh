#!/usr/bin/bash

set -e

echo "run backend tests"

./bin/backend-utils.sh poetry run pytest ffun
