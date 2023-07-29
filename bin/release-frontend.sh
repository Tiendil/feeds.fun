#!/usr/bin/bash

set -e

export BUMP_VERSION=$1

cd ./site

echo "Bumping version as $BUMP_VERSION"

export FFUN_VERSION=$(npm version $BUMP_VERSION)
export FFUN_VERSION_TAG="frontend-$FFUN_VERSION"

echo "New version is $FFUN_VERSION"
echo "New version tag $FFUN_VERSION_TAG"

echo "Commit changes"

git add -A
git commit -m "Frontend release ${FFUN_VERSION}"
git push

echo "Create tag"

git tag $FFUN_VERSION_TAG
git push origin $FFUN_VERSION_TAG
