#!/usr/bin/env bash
set -euo pipefail
poetry install

time poetry run python nthp load
time poetry run python nthp stats
time poetry run python nthp dump
