#!/usr/bin/bash

set -e

export BUMP_VERSION=$1

echo "Bumping version as $BUMP_VERSION"

echo "Bump backend version"

cd ./ffun

export FFUN_VERSION=$(poetry version $BUMP_VERSION --short)
export FFUN_VERSION_TAG="release-$FFUN_VERSION"

echo "Building Python package"

poetry build

echo "Set frontend version"

cd ../site

npm version --tag-version-prefix "" $BUMP_VERSION

echo "New version is $FFUN_VERSION"
echo "New version tag $FFUN_VERSION_TAG"

cd ..

echo "Commit changes"

git add -A
git commit -m "Release ${FFUN_VERSION}"
git push

echo "Create tag"

git tag $FFUN_VERSION_TAG
git push origin $FFUN_VERSION_TAG
