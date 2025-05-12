#!/usr/bin/env python3
import asyncio
import argparse
import logging
import re
import uuid
import random

from cheat.irc_client import IrcClient

BROADCASTER_NAME = "broadcaster"
PEOPLE_NAMES = ("Alice", "Bob", "Eve")

line_rxp = re.compile(f"^([tq])$")
mine_rxp = re.compile(f"^INV:(?P<[0-9a-f]{8}):(?P<nonce>\d+)$")


class RandomTransaction:

    def __init__(self):
        self._uid = uuid.uuid4().hex[:8]
        self.msg = self.generate_random_message()

    @property
    def uid(self):
        return self._uid

    @staticmethod
    def generate_random_message() -> str:
        first = random.choice(PEOPLE_NAMES)
        second = random.choice(list(set(PEOPLE_NAMES) - {first}))
        amount = random.randint(1, 100)
        return f"{first} sends {amount} to {second}"

    @property
    def message(self):
        return f"MSG:{self.uid}:{self.msg}"


class Game:
    def __init__(self):
        self.transactions = {}

    def create_transaction(self):
        tr = RandomTransaction()
        self.transactions[tr.uid] = tr
        return tr


class Broadcaster(IrcClient):
    """The broadcaster"""

    def __init__(self):
        self.difficulty = 1
        self.channel = "pycon"

    async def process(self, src: str, cmd: str, msgs: list[str]) -> None:
        if src == "PING":
            await self.send("PONG")
            logging.info("Received PING, sent PONG")
        else:
            logging.info("%s", (src, cmd, msgs))


async def async_input(prompt: str = '') -> str:
    """
    Asynchronous wrapper around the built-in input function.
    """
    return await asyncio.get_event_loop().run_in_executor(
        None,
        input,
        prompt,
    )


async def cli(client: Broadcaster) -> None:
    """Command line interface to the Broadcaster"""
    await client.join_channel(client.channel)

    game = Game()

    while True:
        try:
            line = await async_input(">>> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        else:
            matched = line_rxp.match(line)
            if matched:
                cmd, *args = matched.groups()
                if cmd == "t":
                    tr = game.create_transaction()
                    await client.send_message(
                        client.channel,
                        tr.message
                    )


async def main():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host",
        default="localhost",
        help="IRC server host to connect to"
    )
    parser.add_argument(
        "-c",
        "--channel",
        default="pycon",
        help="IRC channel to join"
    )
    args = parser.parse_args()
    client = Broadcaster()
    await client.connect(server_host=args.host)
    await client.set_user(BROADCASTER_NAME)
    await client.set_nick(BROADCASTER_NAME)
    logging.info("Connected to %s:%s", args.host, args.channel)
    try:
        await asyncio.gather(
            client.handle_forever(handlers=(client.process,)),
            cli(client),
            return_exceptions=True
        )
    finally:
        await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
