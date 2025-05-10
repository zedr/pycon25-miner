#!/usr/bin/env python3
import hashlib
import argparse


def sha256hash(s: str) -> str:
    """Get the md5 hash of the given string"""
    return hashlib.sha256(s.encode()).hexdigest()


def verify(hashed: str, difficulty: int) -> bool:
    """Verify the nonce of a transaction message"""
    return hashed[:difficulty] == "0" * difficulty


def mine(text: str, difficulty: int, begin_nonce: int) -> tuple[int, str]:
    """Mine the text at the given difficulty

    The nonce and the text are merged
    """
    nonce = begin_nonce
    while True:
        to_hash = f"{nonce}:{text}"
        hashed = sha256hash(to_hash)
        if verify(hashed, difficulty):
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
    found_nonce, hsh = mine(args.text, args.difficulty, 1)
    print(found_nonce)
    print(hsh)


if __name__ == "__main__":
    main()
