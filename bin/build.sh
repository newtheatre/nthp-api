#!/usr/bin/env bash
set -euo pipefail

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Build the project
time uv run python nthp load
time uv run python nthp stats
time uv run python nthp dump
