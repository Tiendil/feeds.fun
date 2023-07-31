#!/bin/bash

set -e

echo "apply migraions"

ffun migrate

echo "migrations successfull"

exec "$@"
