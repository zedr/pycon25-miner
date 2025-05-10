#!/usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset

echo "-> Running ruff"
ruff check .
echo "-> Running pyright"
pyright *.py
