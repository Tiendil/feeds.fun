#!/usr/bin/bash

set -e

export BUMP_VERSION=$1

cd ./ffun

echo "Bumping version as $BUMP_VERSION"

export FFUN_VERSION=$(poetry version $BUMP_VERSION --short)
export FFUN_VERSION_TAG="python-$FFUN_VERSION"

echo "New version is $FFUN_VERSION"
echo "New version tag $FFUN_VERSION_TAG"

echo "Building Python package"

poetry build

echo "Commit changes"

git add -A
git commit -m "Python release ${FFUN_VERSION}"
git push

echo "Create tag"

git tag $FFUN_VERSION_TAG
git push origin $FFUN_VERSION_TAG
