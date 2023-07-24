#!/usr/bin/bash

echo "run isort"

./bin/backend-utils.sh poetry run isort .

echo "run black"

./bin/backend-utils.sh poetry run black .

echo "run prettier"

./bin/frontend-utils.sh ls -lah

echo "????"

./bin/frontend-utils.sh npm run format
