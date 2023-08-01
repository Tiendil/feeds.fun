#!/bin/bash

set -e

echo "apply migraions"

ffun migrate

echo "migrations successfull"

# TODO: remove
echo "-------------------------"
echo $FFUN_AUTH_MODE
echo "-------------------------"

exec "$@"
