import asyncio
import random

from telethon.errors import FloodWaitError


async def handle_flood_wait(error: FloodWaitError):
    wait_time = error.seconds + 5
    await asyncio.sleep(wait_time)


async def safe_sleep(delay: float, custom_jitter: float = 1.0):
    jitter = random.uniform(0, custom_jitter)
    await asyncio.sleep(delay + jitter)
