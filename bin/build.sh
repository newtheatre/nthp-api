#!/usr/bin/env bash
set -euo pipefail

# Install poetry
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -

# Install dependencies
poetry install

# Build the project
time poetry run python nthp load
time poetry run python nthp stats
time poetry run python nthp dump
