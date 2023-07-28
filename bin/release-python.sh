#!/usr/bin/bash

set -e

export BUMP_VERSION=$1

cd ./ffun

echo "Bumping version as $BUMP_VERSION"

export FFUN_VERSION=$(poetry version $BUMP_VERSION --short)

echo "New version is $FFUN_VERSION"

echo "Building Python package"

poetry build
