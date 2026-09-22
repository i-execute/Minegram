#!/usr/bin/env python3
"""Minegram — TG bot for Minecraft server control (GoyGram MTProto)."""
import asyncio

from kernel import kernel


async def main():
    await kernel.init()
    await kernel.run()


if __name__ == "__main__":
    asyncio.run(main())
