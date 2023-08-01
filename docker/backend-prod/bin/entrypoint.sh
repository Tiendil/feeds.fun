#!/bin/bash

set -e

echo "apply migraions"

ffun migrate

echo "migrations successfull"

# TODO: remove
echo "-------------------------"
ffun print-configs
echo "-------------------------"

exec "$@"
