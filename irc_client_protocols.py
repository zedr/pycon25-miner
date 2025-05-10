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
