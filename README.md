# PyCon Italia '25
## Cryptominer workshop

# Requirements
 - Python 3.10 or better

# Workshop slides
See the [slides.pdf](slides.pdf) file.

# Installation
 1. Create a virtual environment local to this repo
    ```bash
    python3 -m venv .env
    ```
 2. Activate it
    ```bash
    source .env/bin/activate
    ```

# Usage
## Tests
 1. Run the test suite
    ```bash
    python3 irc_client_tests.py
    ```

## Local IRC server
 1. Run the ircd server as a daemon in Podman or Docker, e.g.
    ```bash
    podman run -p6667:6667 --name ircd -d -t docker.io/zedr77/pycon25-ircd
    ```

 2. Join the server by running the [irc_client.py](irc_client.py) script:
    ```bash
    ./irc_client.py satoshi
    ```
