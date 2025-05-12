#!/usr/bin/env python3
import asyncio
import argparse
import logging
from typing import Callable, Sequence, Awaitable, Optional

from cheat.irc_client import IrcClient
from miner import mine


class MinerClient(IrcClient):
    def __init__(self):
        super().__init__()
        self.current_channel = None

    async def join_channel(self, channel_name: str) -> None:
        await super().join_channel(channel_name)
        self.current_channel = channel_name

    async def mine(self, src, cmd, msgs) -> bool:
        try:
            channel, *rest = msgs
        except ValueError:
            return False

        channel: str
        if channel.lstrip("#") == self.current_channel:
            msg = " ".join(rest)
            try:
                _, cmd, message_id, difficulty, message = msg.split(":")
            except ValueError:
                print(f"Ignored {src} {cmd} {msgs}")
            else:
                if cmd == "TX":
                    print(f"Mining")
                    tup = mine(message.strip(), int(difficulty), 1)
                    nonce, hsh = tup
                    print(hsh)
                    await self.send_message(
                        self.current_channel,
                        f"INV:{difficulty}:{message_id}:{nonce}"
                    )


async def main():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "NAME",
        help="The user and nickname",
    )
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
    client = MinerClient()
    await client.connect(server_host=args.host)
    await client.set_user(args.NAME)
    await client.set_nick(args.NAME)
    await client.join_channel(args.channel)
    await client.send_message(args.channel, "HELLO")
    try:
        await client.handle_forever(
            handlers=(
                client.mine,
            )
        )
    finally:
        await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
