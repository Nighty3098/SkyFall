from __future__ import annotations

import asyncio
import os
import re
from collections.abc import Callable

from loguru import logger
from telethon import TelegramClient, utils
from telethon.errors import (
    AccessTokenExpiredError,
    AccessTokenInvalidError,
    FloodWaitError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
)
from telethon.sessions import StringSession

try:
    from telethon import connection as _telethon_connection

    _CONNECTION = _telethon_connection
except ImportError:
    _CONNECTION = None

from src.modules.tg.proxy import get_working_proxy, load_proxies, parse_proxies_text
from src.modules.tg.state import CollectorState
from src.modules.tg.throttler import handle_flood_wait, safe_sleep

BASE_DELAY = 2
CONNECT_TIMEOUT = 120
DIALOGS_SCAN_LIMIT = 500
MAX_PROXY_ROTATIONS = 20
MAX_RETRIES = 3
SESSION_NAME = "tg_session.session"

_USERNAME_RE = re.compile(r"[A-Za-z0-9_]{4,32}")
_BOT_TOKEN_RE = re.compile(r"\d{5,}:[A-Za-z0-9_-]{30,}")
_TME_LINK_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me|telegram\.dog)/(.+)$",
    re.IGNORECASE,
)
_RESERVED_PATHS = {
    "joinchat", "c", "s", "addstickers", "addtheme", "share", "iv", "proxy", "socks",
}


class TgOSINT:
    def __init__(self, config: dict, log_callback: Callable = logger.info):
        self.config = config
        self.log_callback = log_callback
        self.api_id = config.get("api_id")
        self.api_hash = config.get("api_hash")
        self.session_path = config.get("session_path") or config.get("path") or "."
        self.base_delay = config.get("base_delay", BASE_DELAY)

        self.state = CollectorState()
        self.client: TelegramClient | None = None
        self._proxy_ready = False
        self._id_cache: dict[str, tuple[int, int]] = {}  # username -> (raw_id, marked_id)
        self._username_cache: dict[int, str] = {}

    async def get_id_by_username(
        self, username: str, *, marked: bool = False
    ) -> int | None:
        uname = self._normalize_username(username)
        if uname is None:
            self.log_callback(f"Invalid username: {username!r}")
            return None

        key = uname.lower()
        cached = self._id_cache.get(key)
        if cached is not None:
            return cached[1] if marked else cached[0]

        if not await self._ensure_client():
            return None

        for _ in range(MAX_RETRIES):
            try:
                entity = await self.client.get_entity(uname)
                raw_id = int(entity.id)
                marked_id = int(utils.get_peer_id(entity))
                self._id_cache[key] = (raw_id, marked_id)
                await safe_sleep(self.base_delay)
                return marked_id if marked else raw_id
            except FloodWaitError as e:
                await handle_flood_wait(e)
            except (UsernameNotOccupiedError, UsernameInvalidError):
                self.log_callback(f"Username @{uname} is not occupied or invalid")
                return None
            except ValueError as e:
                self.log_callback(f"Could not resolve @{uname}: {e}")
                return None
            except Exception as e:
                self.log_callback(f"Error resolving @{uname}: {e}")
                return None

        self.log_callback(f"Could not resolve @{uname}: retries exhausted (FloodWait)")
        return None

    async def get_username_by_id(self, user_id: int | str) -> str | None:
        try:
            peer_id = int(str(user_id).strip())
        except (TypeError, ValueError):
            self.log_callback(f"Invalid id: {user_id!r}")
            return None

        if peer_id in self._username_cache:
            return self._username_cache[peer_id]

        if not await self._ensure_client():
            return None

        entity = None
        for _ in range(MAX_RETRIES):
            try:
                entity = await self.client.get_entity(peer_id)
                break
            except FloodWaitError as e:
                await handle_flood_wait(e)
            except (ValueError, TypeError):
                entity = await self._find_entity_in_dialogs(peer_id)
                break
            except Exception as e:
                self.log_callback(f"Error resolving id {peer_id}: {e}")
                return None

        if entity is None:
            self.log_callback(
                f"Id {peer_id} not found (entity is not in session cache or dialogs)"
            )
            return None

        username = getattr(entity, "username", None)
        await safe_sleep(self.base_delay)
        if username:
            self._username_cache[peer_id] = username
            return username

        self.log_callback(f"Entity {peer_id} has no public username")
        return None

    async def get_username_by_bot_token(self, bot_token: str) -> str | None:
        token = (bot_token or "").strip()
        if not _BOT_TOKEN_RE.fullmatch(token):
            self.log_callback("Invalid bot token format")
            return None

        api_id, api_hash = self._get_env_creds()
        if not api_id or not api_hash:
            self.log_callback(
                "API_ID and API_HASH are required. "
                "Fill in the fields or set API_ID/API_HASH env vars."
            )
            return None

        if not self._proxy_ready:
            await self._setup_proxy()

        bot_client = self._build_client(StringSession(), api_id, api_hash)
        if bot_client is None:
            return None

        try:
            for _ in range(MAX_RETRIES):
                try:
                    await asyncio.wait_for(
                        bot_client.start(bot_token=token), timeout=CONNECT_TIMEOUT
                    )
                    break
                except FloodWaitError as e:
                    await handle_flood_wait(e)
            else:
                self.log_callback(
                    "Bot authorization failed: retries exhausted (FloodWait)"
                )
                return None

            me = await bot_client.get_me()
            username = getattr(me, "username", None)
            if username:
                self.log_callback(
                    f"Bot token is valid: @{username} (id={getattr(me, 'id', 'N/A')})"
                )
                return username
            self.log_callback("Bot has no username")
            return None
        except (AccessTokenInvalidError, AccessTokenExpiredError):
            self.log_callback("Bot token is invalid or expired")
            return None
        except Exception as e:
            self.log_callback(f"Error checking bot token: {e}")
            return None
        finally:
            try:
                await bot_client.disconnect()
            except Exception:
                pass

    async def close(self):
        if self.client is not None:
            try:
                await self.client.disconnect()
            except Exception:
                pass
            self.client = None

    def set_proxy(self, proxy_url: str | None, use_proxy: bool = True):
        """Update the proxy configuration.

        Forces proxy re-detection on the next connection attempt so that
        changes to the UI (e.g. toggling "Use system proxy") take effect
        without restarting the application.
        """
        self.config["proxy_list"] = proxy_url or ""
        self.config["use_proxy"] = bool(use_proxy and proxy_url)
        self._proxy_ready = False

    async def __aenter__(self) -> TgOSINT:
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    def _get_env_creds(self):
        env_api_id = os.getenv("API_ID", "")
        env_api_hash = os.getenv("API_HASH", "")
        return self.api_id or env_api_id, self.api_hash or env_api_hash

    @staticmethod
    def _normalize_username(raw: str) -> str | None:
        """'@name' / 't.me/name/123' / 'tg://resolve?domain=name' -> 'name'."""
        if not isinstance(raw, str) or not raw.strip():
            return None
        value = raw.strip()

        link = _TME_LINK_RE.match(value)
        if link:
            value = link.group(1)
        elif value.lower().startswith("tg://resolve"):
            domain = re.search(r"[?&]domain=([^&]+)", value, re.IGNORECASE)
            if not domain:
                return None
            value = domain.group(1)

        value = value.split("?", 1)[0].split("/", 1)[0].strip().lstrip("@")
        if not value or value.startswith("+") or value.lower() in _RESERVED_PATHS:
            return None
        if not _USERNAME_RE.fullmatch(value):
            return None
        return value

    async def _find_entity_in_dialogs(self, peer_id: int):

        def _bare(value: int) -> int:
            s = str(abs(value))
            return int(s[3:]) if s.startswith("100") else int(s)

        target = _bare(peer_id)
        try:
            async for dialog in self.client.iter_dialogs(limit=DIALOGS_SCAN_LIMIT):
                entity = dialog.entity
                eid = getattr(entity, "id", None)
                if eid is None:
                    continue
                if (
                    utils.get_peer_id(entity) == peer_id
                    or eid == peer_id
                    or _bare(eid) == target
                ):
                    return entity
        except Exception as e:
            self.log_callback(f"Error scanning dialogs for id {peer_id}: {e}")
        return None

    async def _setup_proxy(self):
        self.state.proxies.clear()
        self.state.current_proxy = None
        self.state.use_proxy = self.config.get("use_proxy", False)
        proxy_list_str = self.config.get("proxy_list", "")

        if self.state.use_proxy and proxy_list_str:
            self.state.proxies = parse_proxies_text(proxy_list_str)
        elif os.path.exists(os.path.join(self.session_path, "resources/proxies.txt")):
            self.state.proxies = load_proxies(
                os.path.join(self.session_path, "resources/proxies.txt")
            )

        if self.state.use_proxy and self.state.proxies:
            self.log_callback(f"Loaded {len(self.state.proxies)} proxies")
            self.state.current_proxy = get_working_proxy(
                self.state.proxies, max_attempts=8
            )
            if self.state.current_proxy:
                if isinstance(self.state.current_proxy, tuple):
                    _, host, port, *_ = self.state.current_proxy
                    self.log_callback(f"Using working proxy: {host}:{port}")
                else:
                    self.log_callback(
                        f"Using working proxy: {self.state.current_proxy.get('addr')}:"
                        f"{self.state.current_proxy.get('port')}"
                    )
            else:
                self.log_callback("No working proxies found. Continuing without proxy.")
                self.state.use_proxy = False
                self.state.current_proxy = None
        else:
            self.log_callback("Proxy disabled or no proxies loaded.")
        self._proxy_ready = True

    def _build_client(self, session, api_id, api_hash) -> TelegramClient | None:
        aid = int(api_id)
        ah = api_hash
        try:
            proxy = self.state.current_proxy if self.state.use_proxy else None
            if isinstance(proxy, tuple) and len(proxy) >= 3:
                ptype, host, port = proxy[0], proxy[1], proxy[2]
                secret = proxy[3] if len(proxy) > 3 else None

                if ptype == "mtproto" and secret:
                    self.log_callback(f"Connecting via MTProto: {host}:{port}")
                    if _CONNECTION and hasattr(
                        _CONNECTION, "ConnectionTcpMTProxyRandomizedIntermediate"
                    ):
                        return TelegramClient(
                            session,
                            aid,
                            ah,
                            connection=_CONNECTION.ConnectionTcpMTProxyRandomizedIntermediate,
                            proxy=(host, int(port), str(secret)),
                            timeout=5,
                        )
                    return TelegramClient(
                        session, aid, ah,
                        proxy=(host, int(port), str(secret)), timeout=5,
                    )

                user = proxy[3] if len(proxy) > 3 and proxy[3] else None
                password = proxy[4] if len(proxy) > 4 and proxy[4] else None
                proxy_dict = {
                    "addr": str(host),
                    "port": int(port),
                    "proxy_type": (
                        ptype if ptype in ("socks5", "socks4", "http") else "socks5"
                    ),
                }
                if user and password:
                    proxy_dict["username"] = str(user)
                    proxy_dict["password"] = str(password)
                self.log_callback(f"Connecting via {ptype}: {host}:{port}")
                return TelegramClient(session, aid, ah, proxy=proxy_dict, timeout=5)

            return TelegramClient(session, aid, ah, timeout=5)
        except Exception as e:
            self.log_callback(f"Failed to create Telegram client: {e}")
            return None

    async def _ensure_client(self) -> bool:
        """Lazily connect the user client with proxy rotation."""
        if self.client is not None and self.client.is_connected() and self._proxy_ready:
            return True

        api_id, api_hash = self._get_env_creds()
        if not api_id or not api_hash:
            self.log_callback(
                "API_ID and API_HASH are required. "
                "Fill in the fields or set API_ID/API_HASH env vars."
            )
            return False

        if not self._proxy_ready:
            await self._setup_proxy()

        if self.client is not None:
            try:
                await self.client.disconnect()
            except Exception:
                pass
            self.client = None

        session_path = os.path.join(os.path.abspath(self.session_path), SESSION_NAME)
        self.client = self._build_client(session_path, api_id, api_hash)
        if self.client is None:
            return False

        async def _no_interactive_phone():
            raise RuntimeError(
                "Session is not authorized and interactive login is not supported"
            )

        for rotation in range(MAX_PROXY_ROTATIONS):
            try:
                await asyncio.wait_for(
                    self.client.start(phone=_no_interactive_phone),
                    timeout=CONNECT_TIMEOUT,
                )
                break
            except RuntimeError as e:
                self.log_callback(f"Authorization error: {e}")
                return False
            except Exception as e:
                self.log_callback(f"Connection error: {e}")
                if not self.state.use_proxy:
                    return False
                self.state.remove_current_proxy()
                self.state.rotate_proxy()
                if not self.state.current_proxy:
                    self.log_callback("No more proxies available")
                    return False
                self.log_callback(
                    f"Rotating proxy ({rotation + 1}/{MAX_PROXY_ROTATIONS})..."
                )
                self.client = self._build_client(session_path, api_id, api_hash)
                if self.client is None:
                    return False
        else:
            self.log_callback("Failed to connect with all proxies")
            return False

        if not await self.client.is_user_authorized():
            self.log_callback("User not authorized.")
            return False

        self.log_callback("Client authorized successfully!")
        return True
