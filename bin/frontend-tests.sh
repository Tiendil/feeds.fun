#!/usr/bin/bash

set -e

echo "run frontend tests"

./bin/frontend-utils.sh npm run test:unit -- --run
