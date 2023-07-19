#!/usr/bin/bash

set -e

./bin/backend-utils.sh poetry run isort --check-only .
