#!/usr/bin/env python3
import hashlib
import argparse
from typing import Optional


def sha256hash(s: str) -> str:
    """Get the md5 hash of the given string"""
    return hashlib.sha256(s.encode()).hexdigest()


def verify(hashed: str, difficulty: int) -> bool:
    """Verify the nonce of a transaction message"""
    return hashed[:difficulty] == "0" * difficulty


def validate(nonce: int, message: str, difficulty: int) -> Optional[str]:
    """Validate the nonce for a given message and difficulty

    If valid, return the found hash, else return nothing.
    """
    to_hash = f"{nonce}:{message}"
    hashed = sha256hash(to_hash)
    if verify(hashed, difficulty):
        return hashed


def mine(text: str, difficulty: int, begin_nonce: int) -> tuple[int, str]:
    """Mine the text at the given difficulty

    The nonce and the text are merged
    """
    nonce = begin_nonce
    while True:
        if hashed := validate(nonce, text, difficulty):
            return (nonce, hashed)
        else:
            nonce += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "difficulty",
        help="The difficulty to use",
        type=int,
    )
    parser.add_argument(
        "text",
        help="The text to mine"
    )
    args = parser.parse_args()
    try:
        found_nonce, hsh = mine(args.text, args.difficulty, 1)
    except KeyboardInterrupt:
        pass
    else:
        print(found_nonce)
        print(hsh)


if __name__ == "__main__":
    main()
