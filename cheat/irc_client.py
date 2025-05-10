#!/usr/bin/env python3

import asyncio


class IrcClient:
    pass


async def main():
    client = IrcClient()
    await client.connect()
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
