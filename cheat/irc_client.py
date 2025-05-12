#!/usr/bin/env python3
import asyncio
import argparse
import logging
from typing import Callable, Sequence, Awaitable, Optional


class IrcClient:
    async def connect(
            self, server_host: str = "127.1", server_port: int = 6667
    ) -> None:
        """Connect to an IRC server"""
        self.reader, self.writer = await asyncio.open_connection(
            server_host, server_port
        )

    async def disconnect(self) -> None:
        """Disconnect from the IRC server"""
        self.writer.close()
        await self.writer.wait_closed()

    async def send(self, message: str) -> None:
        """Send a message to the server"""
        self.writer.write(message.encode() + b"\r\n")
        await self.writer.drain()

    async def set_nick(self, nick_name: str) -> None:
        """Set the nick of the client"""
        await self.send(f"NICK {nick_name}")

    async def set_user(self, user_name: str) -> None:
        """Set the user identity of the client"""
        await self.send(f"USER {user_name} 0 * :{user_name}")

    async def join_channel(self, channel_name: str) -> None:
        """Join a channel"""
        await self.send(f"JOIN #{channel_name}")

    async def send_message(self, channel_name: str, message: str) -> None:
        """Send a message to the given channel"""
        await self.send(f"PRIVMSG #{channel_name} :{message}")

    async def handle_forever(
            self,
            handlers: Sequence[
                Callable[[str, str, list[str]], Awaitable[Optional[bool]]]
            ] = (),
    ) -> None:
        """Handle an incoming message from the server"""
        while True:
            line = await self.reader.readline()
            if line:
                message = line.decode().strip()
                source, cmd, *words = message.split(" ")
                for handler in handlers:
                    await handler(source, cmd, words)

    @staticmethod
    async def echo(src: str, cmd: str, msgs: list[str]) -> None:
        logging.debug("%s", (src, cmd, msgs))


# Alias as a function for importing in tests
echo = IrcClient.echo


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
    client = IrcClient()
    await client.connect(server_host=args.host)
    await client.set_user(args.NAME)
    await client.set_nick(args.NAME)
    await client.join_channel(args.channel)
    await client.send_message(args.channel, "HELLO")
    try:
        await client.handle_forever(handlers=(client.echo,))
    finally:
        await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
