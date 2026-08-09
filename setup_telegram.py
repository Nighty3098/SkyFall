"""Interactive Telegram authorization script.

Creates a session file that can be reused by the main app.
Usage:
    python setup_telegram.py [--path /path/to/storage] [--api-id 12345] [--api-hash abcdef]
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from telethon import TelegramClient
from telethon.network import connection as _connection


def load_mtproto_proxy() -> tuple | None:
    proxies_file = Path.home() / ".skyfall" / "proxies.txt"
    if not proxies_file.exists():
        return None

    lines = proxies_file.read_text().strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if "t.me/proxy" in line or "tg://proxy" in line:
            from urllib.parse import parse_qs, urlparse

            try:
                if "t.me/proxy" in line:
                    line = line.replace("https://t.me/proxy", "tg://proxy")
                params = parse_qs(urlparse(line).query)
                server = params.get("server", [""])[0]
                port = int(params.get("port", ["443"])[0])
                secret = params.get("secret", [""])[0]
                if server and secret:
                    return (server, port, secret)
            except Exception:
                continue
        break
    return None


async def main():
    parser = argparse.ArgumentParser(description="Telegram session setup")
    parser.add_argument(
        "--path", default=os.getcwd(), help="Storage path for session file"
    )
    parser.add_argument("--api-id", help="Telegram API ID")
    parser.add_argument("--api-hash", help="Telegram API hash")
    args = parser.parse_args()

    api_id = (
        args.api_id
        or os.getenv("API_ID")
        or (await asyncio.to_thread(input, "API ID: ")).strip()
    )
    api_hash = (
        args.api_hash
        or os.getenv("API_HASH")
        or (await asyncio.to_thread(input, "API Hash: ")).strip()
    )

    if not api_id or not api_hash:
        print("API_ID and API_HASH are required")
        sys.exit(1)

    path = os.path.abspath(args.path)
    os.makedirs(path, exist_ok=True)
    session_path = os.path.join(path, "tg_session.session")

    proxy = load_mtproto_proxy()
    if proxy:
        host, port, secret = proxy
        print(f"Using MTProto proxy: {host}:{port}")
        client = TelegramClient(
            session_path,
            int(api_id),
            api_hash,
            connection=_connection.ConnectionTcpMTProxyRandomizedIntermediate,
            proxy=(host, port, str(secret)),
            timeout=10,
        )
    else:
        client = TelegramClient(session_path, int(api_id), api_hash, timeout=10)

    await client.start()
    print(f"\nSession saved: {session_path}")
    print(f"Authorized as: {(await client.get_me()).username or 'unknown'}")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
