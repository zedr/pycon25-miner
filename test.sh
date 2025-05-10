#!/usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset

echo "-> Running tests"
/usr/bin/env python3 irc_client_tests.py
