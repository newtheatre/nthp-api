#!/usr/bin/env bash

set -euo pipefail

# Ensure we are on the master branch, failing the script if not
if [[ $(git rev-parse --abbrev-ref HEAD) != "master" ]]; then
    echo "Not on master branch, aborting."
    exit 1
fi

# Ensure working directory is clean
if [[ -n $(git status --porcelain) ]]; then
    echo "Working directory not clean, aborting."
    exit 1
fi

# Bump version of the project, using argument (e.g. patch/minor/major)
uv version --bump "$1"
VERSION=$(uv version --short)

# Commit that change and tag
git add pyproject.toml uv.lock
git commit -m "Bump version to $VERSION"
git tag -a "v$VERSION" -m "v$VERSION"

# Build and publish to PyPI
uv build
uv publish

# Push to GitHub
git push origin master
git push origin "v$VERSION"
