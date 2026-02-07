#!/usr/bin/bash

set -e

echo "run backend codespell"

./bin/backend-utils.sh poetry run codespell --toml pyproject.toml ./ffun

echo "run frontend codespell"

./bin/frontend-utils.sh codespell --toml /repository/codespell.toml ./src
