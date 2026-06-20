from __future__ import annotations

import asyncio
import os

from loguru import logger
from telethon import TelegramClient

try:
    from telethon import connection as _telethon_connection

    _CONNECTION = _telethon_connection
except ImportError:
    _CONNECTION = None

from src.modules.tg.state import CollectorState

PROXY_ERRORS = (
    "Server closed the connection",
    "Connection timed out",
    "Graceful disconnection timed out",
    "Proxy closed the connection",
    "ConnectionError",
    "ConnectionRefusedError",
    "TimeoutError",
)


def get_session_for_proxy(proxy_tuple: tuple, base_session_name: str, path: str) -> str:
    if not proxy_tuple or proxy_tuple[0] != "mtproto":
        return os.path.join(os.path.abspath(path), base_session_name)
    _, host, port, *_ = proxy_tuple
    proxy_hash = abs(hash(f"{host}:{port}")) % 100000
    session_name_str = f"session_{proxy_hash}.session"
    return os.path.join(os.path.abspath(path), session_name_str)


def cleanup_session_for_new_proxy(
    session_path: str, proxy_tuple: tuple, path: str
) -> str:
    if proxy_tuple and proxy_tuple[0] == "mtproto":
        new_session_path = get_session_for_proxy(proxy_tuple, "session", path)
        if os.path.exists(new_session_path):
            try:
                os.remove(new_session_path)
            except Exception:
                pass
        return new_session_path
    return session_path


def is_proxy_error(error: Exception) -> bool:
    error_str = str(error).lower()
    return any(e.lower() in error_str for e in PROXY_ERRORS)


async def recreate_client_with_new_proxy(
    client: TelegramClient,
    session_path: str,
    api_id: str,
    api_hash: str,
    state: CollectorState,
) -> TelegramClient:
    if client:
        try:
            await client.disconnect()
        except Exception:
            pass

    if not state.proxies:
        raise Exception("No proxies available")

    state.rotate_proxy()
    new_proxy = state.current_proxy
    if not new_proxy:
        raise Exception("No proxies available")

    ptype, host, port = new_proxy[0], new_proxy[1], new_proxy[2]
    secret = new_proxy[3] if len(new_proxy) > 3 else None

    if ptype == "mtproto" and secret:
        logger.info(f"Connecting via MTProto: {host}:{port}")
        conn_class = (
            _CONNECTION.ConnectionTcpMTProxyRandomizedIntermediate
            if _CONNECTION
            and hasattr(_CONNECTION, "ConnectionTcpMTProxyRandomizedIntermediate")
            else None
        )
        kwargs = {
            "session": session_path,
            "api_id": int(api_id),
            "api_hash": api_hash,
            "proxy": (host, int(port), str(secret)),
            "timeout": 10,
        }
        if conn_class:
            kwargs["connection"] = conn_class
        new_client = TelegramClient(**kwargs)
    else:
        user = new_proxy[3] if len(new_proxy) > 3 and new_proxy[3] else None
        password = new_proxy[4] if len(new_proxy) > 4 and new_proxy[4] else None
        proxy_dict = {
            "addr": str(host),
            "port": int(port),
            "proxy_type": ptype if ptype in ("socks5", "socks4", "http") else "socks5",
        }
        if user and password:
            proxy_dict["username"] = str(user)
            proxy_dict["password"] = str(password)
        logger.info(f"Connecting via {ptype}: {host}:{port}")
        new_client = TelegramClient(
            session_path, int(api_id), api_hash, proxy=proxy_dict, timeout=10
        )

    max_retries = 3
    for attempt in range(max_retries):
        try:
            await new_client.connect()
            if await new_client.is_user_authorized():
                logger.info("Connected with new proxy")
                return new_client
            await new_client.start()
            return new_client
        except Exception as e:
            logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
            state.remove_current_proxy()
            if not state.proxies:
                raise
            await asyncio.sleep(2)
            continue

    raise Exception("Failed to connect with new proxy")
