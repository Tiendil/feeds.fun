#!/bin/bash

set -e

echo "apply migraions"

yoyo apply

echo "migrations successfull"

exec "$@"
