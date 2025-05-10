from asyncio import StreamWriter, StreamReader
from typing import Protocol
from typing import Callable, Sequence, Awaitable, Optional

IrcMessageHandler = Callable[[str, str, list[str]], Awaitable[Optional[bool]]]


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

    async def join_channel(self, channel_name: str) -> None:
        """Joins a channel"""

    async def send_message(self, channel_name: str, message: str) -> None:
        """Sends a message to the given channel"""

    async def handle_forever(
            self,
            handlers: Sequence[IrcMessageHandler] = (),
    ) -> None:
        """Handle an incoming message from the server"""
