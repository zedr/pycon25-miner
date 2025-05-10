from asyncio import StreamWriter, StreamReader
from typing import Protocol


class AsyncIrcClientProtocol(Protocol):
    """The protocol of an asynchronous IRC client."""

    writer: StreamWriter
    reader: StreamReader

    async def connect(
            self,
            server_host: str,
            server_port: int
    ) -> None:
        """Connects to an IRC server."""

    async def disconnect(self) -> None:
        """Disconnects from an IRC server."""

    async def send(self, message: str) -> None:
        """Sends a message to the IRC server"""

    async def set_user(self, user_name: str) -> None:
        """Sets the name of the user client"""

    async def set_nick(self, nick_name: str) -> None:
        """Sets the nickname of the client user"""
