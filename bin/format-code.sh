#!/usr/bin/bash

echo "run isort"

./bin/backend-utils.sh poetry run isort .

echo "run black"

./bin/backend-utils.sh poetry run black .
