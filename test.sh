#!/usr/bin/env bash

set -o pipefail
set -o errexit
set -o nounset

echo "-> Running tests for irc_client"
/usr/bin/env python3 irc_client_tests.py
echo "-> Running tests for miner"
/usr/bin/env python3 miner_tests.py
