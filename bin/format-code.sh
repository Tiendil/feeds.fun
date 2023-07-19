#!/usr/bin/bash

./bin/backend-utils.sh poetry run isort .
./bin/backend-utils.sh poetry run black .
