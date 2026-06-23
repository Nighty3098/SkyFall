from __future__ import annotations

import asyncio
import os
import random
from collections.abc import Callable

from loguru import logger
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import Message, MessageMediaDocument, MessageMediaPhoto
from telethon.tl.types import User as TgUser

try:
    from telethon import connection as _telethon_connection

    _CONNECTION = _telethon_connection
except ImportError:
    _CONNECTION = None

from src.modules.tg.client_manager import is_proxy_error, recreate_client_with_new_proxy
from src.modules.tg.db import (
    add_discussion,
    add_link,
    add_post,
    bulk_insert_members,
    get_channel_last_member_sync,
    get_existing_discussion,
    get_existing_link,
    get_existing_members,
    get_existing_post,
    get_last_post_id,
    init_db,
    save_channel,
    save_discussion_participant,
    update_channel_member_sync,
)
from src.modules.tg.extractors import extract_links, get_link_type
from src.modules.tg.proxy import get_working_proxy, load_proxies, parse_proxies_text
from src.modules.tg.session_manager import get_random_session, load_multi_acc_sessions
from src.modules.tg.state import CollectorState
from src.modules.tg.throttler import handle_flood_wait, safe_sleep
from src.modules.tg.users import fetch_and_save_full_user, get_cached_entity

BASE_DELAY = 2
LONG_BREAK_DURATION = 60
MAX_CONSECUTIVE_REQUESTS = 100
MEMBER_DELAY = 3
REPLY_DELAY = 1
SESSION_NAME = "tg_session.session"


class TgDownloader:
    def __init__(
        self,
        config: dict,
        log_callback: Callable = logger.info,
        progress_callback: Callable | None = None,
    ):
        self.config = config
        self.log_callback = log_callback
        self.progress_callback = progress_callback

        self.api_id = config.get("api_id")
        self.api_hash = config.get("api_hash")
        self.channel_name = config.get("channel")
        self.path = config.get("path")
        self.collect_members = config.get("collect_members", True)
        self.collect_links = config.get("collect_links", True)
        self.download_media = config.get("download_media", True)
        self.base_delay = config.get("base_delay", BASE_DELAY)
        self.member_delay = config.get("member_delay", MEMBER_DELAY)
        self.max_requests = config.get("max_requests", MAX_CONSECUTIVE_REQUESTS)
        self.pause_duration = config.get("pause_duration", LONG_BREAK_DURATION)
        self.use_proxy = config.get("use_proxy", False)
        self.proxy_list_str = config.get("proxy_list", "")
        logger.debug(f"Loaded: {self.proxy_list_str}")
        self.multi_acc = config.get("multi_acc", False)

        self.state = CollectorState()
        self.semaphore = asyncio.Semaphore(2)
        self.client = None
        self.session = None
        self.channel = None
        self.discussion_chat = None
        self.channel_media_dir = None
        self.MEDIA_DIR = None
        self.MAX_CONCURRENT_DOWNLOADS = 2

    def _get_env_creds(self):
        env_api_id = os.getenv("API_ID", "")
        env_api_hash = os.getenv("API_HASH", "")
        provided_api_id = self.api_id or env_api_id
        provided_api_hash = self.api_hash or env_api_hash
        return provided_api_id, provided_api_hash

    async def run(self):
        self.state.reset()

        logger.info("Starting data collection...")

        provided_api_id, provided_api_hash = self._get_env_creds()
        session_path = os.path.join(os.path.abspath(self.path), SESSION_NAME)
        session_exists = os.path.exists(session_path)

        if not provided_api_id or not provided_api_hash:
            self.log_callback(
                "API_ID and API_HASH are required. Fill in the fields or set API_ID/API_HASH env vars."
            )
            return

        if self.multi_acc:
            self.state.multi_acc_sessions = load_multi_acc_sessions(self.path)
            if self.state.multi_acc_sessions:
                self.log_callback(
                    f"Loaded {len(self.state.multi_acc_sessions)} sessions for multi-account mode"
                )
                self.state.switch_request_threshold = random.randint(50, 150)
                self.log_callback(
                    f"Will switch account after {self.state.switch_request_threshold} requests"
                )
            else:
                self.log_callback("Multi-account mode enabled but no sessions found")
                self.multi_acc = False

        await self._setup_proxy()
        self.MEDIA_DIR = os.path.join(os.path.abspath(self.path), "SkyFall_TG_media")
        self.channel_media_dir = os.path.join(self.MEDIA_DIR, self.channel_name)
        os.makedirs(self.channel_media_dir, exist_ok=True)

        (
            engine,
            session_local,
            telegram_user_model,
            post_model,
            discussion_model,
            member_model,
            link_model,
            channel_model,
        ) = init_db(self.path, self.channel_name)

        self.client = await self._create_client(
            session_path, provided_api_id, provided_api_hash
        )

        if self.client is None:
            return

        try:
            await asyncio.wait_for(self.client.connect(), timeout=15)
        except asyncio.TimeoutError:
            self.log_callback("Connection timed out after 15 seconds")
            return
        except Exception as e:
            self.log_callback(f"Connection failed: {e}")
            return

        async with self.client:
            try:
                self.log_callback("Starting Telegram client...")
                connected = await self._connect_with_rotation(
                    session_path, provided_api_id, provided_api_hash
                )
                if not connected:
                    self.log_callback("Failed to connect with all proxies")
                    return

                if not await self.client.is_user_authorized():
                    self.log_callback("User not authorized.")
                    self.log_callback("Cannot authorize in non-interactive mode.")
                    return

                self.log_callback("Client authorized successfully!")
                self.log_callback("Warming up account...")
            except Exception as e:
                self.log_callback(f"Authorization error: {e}")
                return

            self.session = session_local()
            try:
                self.channel = await self.client.get_entity(self.channel_name)
                self.log_callback(
                    f"Connected to channel: {getattr(self.channel, 'title', self.channel_name)}"
                )
                save_channel(self.session, channel_model, self.channel)

                full_channel = await self.client(GetFullChannelRequest(self.channel))
                linked_chat_id = full_channel.full_chat.linked_chat_id

                if linked_chat_id:
                    try:
                        self.discussion_chat = await self.client.get_entity(
                            linked_chat_id
                        )
                        self.log_callback("Found linked discussion chat")
                    except Exception as e:
                        self.log_callback(f"Could not fetch discussion chat: {e}")
                else:
                    self.log_callback("Channel has no linked discussion chat.")

                if self.collect_members:
                    members_ok = await self._collect_channel_members(
                        self.client,
                        self.channel,
                        self.session,
                        member_model,
                        telegram_user_model,
                        channel_model,
                    )
                    if not members_ok:
                        self.log_callback("Collecting members from messages instead...")
                        await self._collect_members_from_messages(
                            self.client,
                            self.channel,
                            self.session,
                            member_model,
                            telegram_user_model,
                            channel_model,
                            self.channel.id,
                        )

                total_messages = (
                    await self.client.get_messages(self.channel, limit=0)
                ).total
                self.log_callback(f"Total messages in channel: {total_messages}")
                self.log_callback("Starting to parse channel messages...")
                if self.progress_callback:
                    self.progress_callback(("channel", 0))

                last_post_id = 0
                last_post_id_db = get_last_post_id(
                    self.session, post_model, self.channel.id
                )
                if last_post_id == 0 and last_post_id_db > 0:
                    self.log_callback(f"Resuming from post ID: {last_post_id_db}")
                elif last_post_id > 0:
                    self.log_callback(f"Resuming from post ID: {last_post_id}")
                else:
                    self.log_callback("Starting fresh download")

                message_counter = 0

                async for message in self.client.iter_messages(
                    self.channel,
                    min_id=last_post_id if last_post_id > 0 else 0,
                    limit=0,
                ):
                    try:
                        await self._process_message(
                            self.client,
                            self.session,
                            message,
                            self.channel_media_dir,
                            self.semaphore,
                            self.channel,
                            self.collect_links,
                            link_model,
                            telegram_user_model,
                            post_model,
                            discussion_model,
                            member_model,
                            channel_model,
                            self.channel.id,
                        )

                        await safe_sleep(self.base_delay)

                        message_counter += 1
                        self.state.request_since_switch += 1

                        if (
                            self.multi_acc
                            and self.state.multi_acc_sessions
                            and self.state.request_since_switch
                            >= self.state.switch_request_threshold
                        ):
                            await self._switch_account(
                                session_path, provided_api_id, provided_api_hash
                            )

                        if self.progress_callback:
                            progress = min(
                                int((message_counter / total_messages) * 100), 100
                            )
                            self.progress_callback(("channel", progress))

                        if message_counter >= self.max_requests:
                            self.log_callback(
                                f"Taking scheduled break of {self.pause_duration} seconds..."
                            )
                            await asyncio.sleep(self.pause_duration)
                            message_counter = 0

                    except FloodWaitError as e:
                        await handle_flood_wait(e)
                        message_counter = 0
                        if self.state.use_proxy:
                            self.state.rotate_proxy()
                    except Exception as e:
                        error_str = str(e).lower()
                        if self.state.use_proxy and (
                            is_proxy_error(e)
                            or "proxy" in error_str
                            or "connection" in error_str
                        ):
                            self.log_callback(f"Proxy/Connection error: {e}")
                            try:
                                self.client = await recreate_client_with_new_proxy(
                                    self.client,
                                    session_path,
                                    self.api_id,
                                    self.api_hash,
                                    self.state,
                                )
                                await safe_sleep(self.base_delay * 2)
                                continue
                            except Exception as reauth_error:
                                self.log_callback(
                                    f"Failed to reconnect: {reauth_error}"
                                )
                                if not self.state.proxies:
                                    self.log_callback(
                                        "No more proxies available, stopping"
                                    )
                                    break

                        self.log_callback(f"Error processing message {message.id}: {e}")
                        await safe_sleep(self.base_delay * 3)

                if self.discussion_chat:
                    self.log_callback("Starting to parse discussion chat...")
                    if self.progress_callback:
                        self.progress_callback(("discussion", 0))
                    await self._fetch_discussion_messages(
                        self.client,
                        self.session,
                        self.discussion_chat,
                        self.channel_media_dir,
                        self.semaphore,
                        self.collect_links,
                        link_model,
                        telegram_user_model,
                        discussion_model,
                        member_model,
                        channel_model,
                        post_model,
                        self.channel.id,
                    )
                    if self.progress_callback:
                        self.progress_callback(("discussion", 100))

                self.log_callback("Download completed!")
                if self.progress_callback:
                    self.progress_callback(("done", 100))

            except Exception as e:
                self.log_callback(f"Error: {e}")
                import traceback

                traceback.print_exc()
            finally:
                self.session.close()

    async def _setup_proxy(self):
        self.state.proxies.clear()
        self.state.current_proxy = None
        self.state.use_proxy = self.config.get("use_proxy", False)
        proxy_list_str = self.config.get("proxy_list", "")

        if self.state.use_proxy and proxy_list_str:
            self.state.proxies = parse_proxies_text(proxy_list_str)
        elif os.path.exists(os.path.join(self.path, "resources/proxies.txt")):
            self.state.proxies = load_proxies(
                os.path.join(self.path, "resources/proxies.txt")
            )

        if self.state.use_proxy and self.state.proxies:
            self.log_callback(f"Loaded {len(self.state.proxies)} proxies")
            self.state.current_proxy = get_working_proxy(
                self.state.proxies, max_attempts=8
            )
            if self.state.current_proxy:
                if (
                    isinstance(self.state.current_proxy, tuple)
                    and self.state.current_proxy[0] == "mtproto"
                ):
                    _, host, port, *_ = self.state.current_proxy
                    self.log_callback(f"Using working MTProto proxy: {host}:{port}")
                elif isinstance(self.state.current_proxy, tuple):
                    _, host, port, *_ = self.state.current_proxy
                    self.log_callback(f"Using working proxy: {host}:{port}")
                else:
                    self.log_callback(
                        f"Using working proxy: {self.state.current_proxy.get('addr')}:{self.state.current_proxy.get('port')}"
                    )
            else:
                self.log_callback("No working proxies found. Continuing without proxy.")
                self.state.use_proxy = False
                self.state.current_proxy = None
        else:
            self.log_callback("Proxy disabled or no proxies loaded.")

    async def _create_client(self, session_path, api_id, api_hash):
        aid = int(api_id)
        ah = api_hash

        try:
            if self.state.use_proxy and self.state.current_proxy:
                if (
                    isinstance(self.state.current_proxy, tuple)
                    and len(self.state.current_proxy) >= 3
                ):
                    ptype, host, port = (
                        self.state.current_proxy[0],
                        self.state.current_proxy[1],
                        self.state.current_proxy[2],
                    )
                    secret = (
                        self.state.current_proxy[3]
                        if len(self.state.current_proxy) > 3
                        else None
                    )
                    if ptype == "mtproto" and secret:
                        self.log_callback(f"Connecting via MTProto: {host}:{port}")
                        if _CONNECTION and hasattr(
                            _CONNECTION, "ConnectionTcpMTProxyRandomizedIntermediate"
                        ):
                            return TelegramClient(
                                session_path,
                                aid,
                                ah,
                                connection=_CONNECTION.ConnectionTcpMTProxyRandomizedIntermediate,
                                proxy=(host, int(port), str(secret)),
                                timeout=5,
                            )
                        return TelegramClient(
                            session_path,
                            aid,
                            ah,
                            proxy=(host, int(port), str(secret)),
                            timeout=5,
                        )
                    else:
                        user = (
                            self.state.current_proxy[3]
                            if len(self.state.current_proxy) > 3
                            and self.state.current_proxy[3]
                            else None
                        )
                        password = (
                            self.state.current_proxy[4]
                            if len(self.state.current_proxy) > 4
                            and self.state.current_proxy[4]
                            else None
                        )
                        proxy_dict = {
                            "addr": str(host),
                            "port": int(port),
                            "proxy_type": (
                                ptype
                                if ptype in ("socks5", "socks4", "http")
                                else "socks5"
                            ),
                        }
                        if user and password:
                            proxy_dict["username"] = str(user)
                            proxy_dict["password"] = str(password)
                        self.log_callback(f"Connecting via {ptype}: {host}:{port}")
                        return TelegramClient(
                            session_path, aid, ah, proxy=proxy_dict, timeout=5
                        )
                else:
                    return TelegramClient(session_path, aid, ah, timeout=5)
            else:
                return TelegramClient(session_path, aid, ah, timeout=5)
        except Exception as e:
            self.log_callback(f"Failed to create Telegram client: {e}")
            return None

    async def _connect_with_rotation(self, session_path, api_id, api_hash):
        connected = False
        max_proxy_rotations = 20

        async def _no_interactive_phone():
            raise RuntimeError(
                "Session is not authorized and interactive login is not supported"
            )

        for rotation in range(max_proxy_rotations):
            try:
                await asyncio.wait_for(
                    self.client.start(phone=_no_interactive_phone),
                    timeout=30,
                )
                connected = True
                break
            except Exception as start_e:
                self.log_callback(f"Error: {start_e}")
                if self.state.use_proxy:
                    self.log_callback(
                        f"Rotating proxy ({rotation + 1}/{max_proxy_rotations})..."
                    )
                    self.state.remove_current_proxy()
                    self.state.rotate_proxy()
                    new_proxy = self.state.current_proxy
                    if new_proxy:
                        self.log_callback(
                            f"New proxy: {new_proxy[1] if isinstance(new_proxy, tuple) else 'unknown'}"
                        )
                        self.client = await self._rebuild_client(
                            new_proxy, session_path, api_id, api_hash
                        )
                        if self.client:
                            try:
                                await asyncio.wait_for(
                                    self.client.connect(), timeout=15
                                )
                            except asyncio.TimeoutError:
                                self.log_callback(
                                    "Reconnect timed out, trying next proxy"
                                )
                                continue
                    continue
                else:
                    raise start_e

        return connected

    async def _rebuild_client(self, new_proxy, session_path, api_id, api_hash):
        aid = int(api_id)
        ah = api_hash

        if isinstance(new_proxy, tuple) and len(new_proxy) >= 3:
            ptype, host, port = new_proxy[0], new_proxy[1], new_proxy[2]
            secret = new_proxy[3] if len(new_proxy) > 3 else None

            if ptype == "mtproto" and secret:
                if _CONNECTION and hasattr(
                    _CONNECTION, "ConnectionTcpMTProxyRandomizedIntermediate"
                ):
                    return TelegramClient(
                        session_path,
                        aid,
                        ah,
                        connection=_CONNECTION.ConnectionTcpMTProxyRandomizedIntermediate,
                        proxy=(host, int(port), str(secret)),
                        timeout=5,
                    )
                return TelegramClient(
                    session_path,
                    aid,
                    ah,
                    proxy=(host, int(port), str(secret)),
                    timeout=5,
                )
            else:
                user = new_proxy[3] if len(new_proxy) > 3 and new_proxy[3] else None
                password = new_proxy[4] if len(new_proxy) > 4 and new_proxy[4] else None
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
                return TelegramClient(
                    session_path, aid, ah, proxy=proxy_dict, timeout=5
                )
        return None

    async def _switch_account(self, session_path, api_id, api_hash):
        aid = int(api_id)
        ah = api_hash

        self.log_callback(
            f"Switching to random account after {self.state.request_since_switch} requests..."
        )
        new_session = get_random_session(self.state.multi_acc_sessions)
        if new_session:
            try:
                if self.client:
                    await self.client.disconnect()
            except Exception:
                pass

            self.client = TelegramClient(new_session, aid, ah, timeout=5)
            await self.client.connect()
            if not await self.client.is_user_authorized():
                self.log_callback(f"Session {new_session} not authorized, skipping...")
                self.state.multi_acc_sessions = [
                    s for s in self.state.multi_acc_sessions if s != new_session
                ]
                return
            self.log_callback(f"Switched to session: {os.path.basename(new_session)}")
            self.state.request_since_switch = 0
            self.state.switch_request_threshold = random.randint(50, 150)
            self.log_callback(
                f"Next switch in {self.state.switch_request_threshold} requests"
            )
            await safe_sleep(self.base_delay * 2)

    async def _collect_channel_members(
        self, client, channel, session, member_model, telegram_user_model, channel_model
    ):
        channel_id = getattr(channel, "id", None)
        last_sync = None
        if channel_id:
            last_sync = get_channel_last_member_sync(session, channel_model, channel_id)

        if last_sync:
            self.log_callback(
                f"Incremental mode: fetching members joined after {last_sync}"
            )
        else:
            self.log_callback(
                f"Collecting ALL members from {getattr(channel, 'title', 'channel')}..."
            )

        members_collected = False
        new_members_data = []
        existing_user_ids = set()

        try:
            total = 0
            member_counter = 0
            async for participant in client.iter_participants(channel):
                try:
                    joined_at = getattr(participant, "joined_at", None)
                    if last_sync and joined_at:
                        joined_str = (
                            joined_at.isoformat()
                            if hasattr(joined_at, "isoformat")
                            else str(joined_at)
                        )
                        if joined_str <= last_sync:
                            continue

                    user_obj = getattr(participant, "user", participant)
                    user_id = getattr(user_obj, "id", None) or getattr(
                        participant, "id", None
                    )

                    if user_id:
                        if (
                            isinstance(user_id, int)
                            and user_id < 0
                            and str(user_id).startswith("-100")
                        ):
                            continue
                        if user_id not in existing_user_ids:
                            existing_user_ids.add(user_id)
                            if isinstance(user_obj, TgUser):
                                await fetch_and_save_full_user(
                                    client,
                                    session,
                                    telegram_user_model,
                                    user_obj,
                                    media_dir=self.channel_media_dir,
                                )

                            date = getattr(participant, "date", None)
                            status = getattr(participant, "status", None)
                            joined_at_str = getattr(participant, "joined_at", date)

                            if date is not None and hasattr(date, "isoformat"):
                                date = date.isoformat()
                            elif date is not None:
                                date = str(date)
                            if joined_at_str is not None and hasattr(
                                joined_at_str, "isoformat"
                            ):
                                joined_at_str = joined_at_str.isoformat()
                            elif joined_at_str is not None:
                                joined_at_str = str(joined_at_str)
                            if status is not None:
                                status = str(status)

                            new_members_data.append(
                                {
                                    "user_id": user_id,
                                    "date": date,
                                    "status": status,
                                    "joined_at": joined_at_str,
                                    "member_type": "member",
                                }
                            )

                        total += 1
                        member_counter += 1
                        members_collected = True

                        if total % 10 == 0:
                            self.log_callback(f"Processed {total} members so far...")
                        if total > 0:
                            await safe_sleep(self.member_delay, custom_jitter=1.0)
                        if member_counter >= 30:
                            self.log_callback(
                                f"Taking a long break of {LONG_BREAK_DURATION} seconds..."
                            )
                            await asyncio.sleep(LONG_BREAK_DURATION)
                            member_counter = 0
                except FloodWaitError as e:
                    await handle_flood_wait(e)
                    await asyncio.sleep(10)
                except Exception as e:
                    self.log_callback(
                        f"Error processing member {getattr(participant, 'id', 'unknown')}: {e}"
                    )
                    await safe_sleep(self.member_delay * 2)
                    continue

            if new_members_data and channel_id:
                existing_ids = get_existing_members(
                    session,
                    member_model,
                    [m["user_id"] for m in new_members_data],
                    channel_id,
                )
                to_insert = [
                    m for m in new_members_data if m["user_id"] not in existing_ids
                ]
                if to_insert:
                    inserted = bulk_insert_members(
                        session, member_model, to_insert, channel_id
                    )
                    self.log_callback(f"Bulk inserted {inserted} new members")

            if channel_id:
                update_channel_member_sync(
                    session,
                    channel_model,
                    channel_id,
                    __import__("datetime").datetime.now().isoformat(),
                )

            self.log_callback(f"Successfully processed {total} members")
        except Exception as e:
            self.log_callback(f"Error collecting members: {e}")

        if not members_collected:
            self.log_callback("Will collect members from messages instead...")
            return False
        return True

    async def _collect_members_from_messages(
        self,
        client,
        channel,
        session,
        member_model,
        telegram_user_model,
        channel_model,
        channel_id,
    ):
        self.log_callback("Collecting members from channel messages...")
        try:
            collected_users = set()
            total = 0
            async for message in client.iter_messages(channel, limit=500):
                if not message.sender_id:
                    continue
                user_id = message.sender_id
                if user_id in collected_users:
                    continue
                if (
                    isinstance(user_id, int)
                    and user_id < 0
                    and str(user_id).startswith("-100")
                ):
                    continue
                try:
                    sender = await get_cached_entity(client, user_id, "user")
                    username = first_name = last_name = None
                    if isinstance(sender, TgUser):
                        await fetch_and_save_full_user(
                            client,
                            session,
                            telegram_user_model,
                            sender,
                            media_dir=self.channel_media_dir,
                        )
                        username = getattr(sender, "username", None)
                        first_name = getattr(sender, "first_name", None)
                        last_name = getattr(sender, "last_name", None)
                    await save_discussion_participant(
                        session,
                        member_model,
                        telegram_user_model,
                        channel_model,
                        user_id,
                        channel_id,
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                        member_type="member",
                    )
                    collected_users.add(user_id)
                    total += 1
                    if total % 10 == 0:
                        self.log_callback(
                            f"Collected {total} message authors so far..."
                        )
                        await safe_sleep(1.0)
                except Exception as e:
                    self.log_callback(f"Error collecting member from message: {e}")
                    continue
            self.log_callback(f"Successfully collected {total} members from messages")
            return True
        except Exception as e:
            self.log_callback(f"Error collecting members from messages: {e}")
            return False

    @staticmethod
    def _get_media_info(message: Message):
        if message.media is None:
            return None, None
        if isinstance(message.media, MessageMediaPhoto):
            return "photo", "jpg"
        if isinstance(message.media, MessageMediaDocument):
            doc = message.media.document
            if doc is None:
                return None, None
            mime_type = getattr(doc, "mime_type", None) or ""
            if not mime_type:
                return "document", "bin"
            if mime_type.startswith("video/"):
                return "video", mime_type.split("/")[-1]
            if mime_type.startswith("audio/"):
                return "audio", mime_type.split("/")[-1]
            return "document", mime_type.split("/")[-1]
        return None, None

    async def _download_media_file(self, client, message, media_type, ext, media_dir):
        if not ext:
            ext = "bin"
        media_path = os.path.join(media_dir, f"{message.id}.{ext}")
        if not os.path.exists(media_path):
            try:
                await client.download_media(message.media, file=media_path)
            except Exception as e:
                self.log_callback(
                    f"Error loading {media_type} for message {message.id}: {e}"
                )
                return None
        return media_path

    async def _download_media_with_semaphore(
        self, message, client, media_dir, semaphore
    ):
        async with semaphore:
            media_type, ext = self._get_media_info(message)
            if media_type:
                return await self._download_media_file(
                    client, message, media_type, ext, media_dir
                )
        return None

    async def _process_links(
        self, session, link_model, message, post_id, channel_id, message_id=None
    ):
        try:
            links = extract_links(message.text or "")
            msg_id = message_id or getattr(message, "id", None)
            for url, context in links:
                existing = get_existing_link(
                    session, link_model, url, post_id, channel_id
                )
                if not existing:
                    add_link(
                        session,
                        link_model,
                        channel_id,
                        url=url,
                        post_id=post_id,
                        message_id=msg_id,
                        date=message.date,
                        text_context=context,
                        link_type=get_link_type(url),
                    )
        except Exception as e:
            self.log_callback(f"Error processing links: {e}")

    async def _process_discussion_replies(
        self,
        client,
        session,
        message,
        channel_media_dir,
        semaphore,
        entity,
        link_model,
        collect_links,
        telegram_user_model,
        discussion_model,
        member_model,
        channel_model,
        channel_id,
    ):
        discussion_dir = os.path.join(channel_media_dir, f"discussion_{message.id}")
        os.makedirs(discussion_dir, exist_ok=True)

        try:
            reply_counter = 0
            async for reply in client.iter_messages(entity, reply_to=message.id):
                try:
                    reply_media_path = await self._download_discussion(
                        client, reply, discussion_dir, semaphore
                    )

                    reply_user_id = None
                    reply_username = None
                    reply_first_name = None
                    reply_last_name = None

                    if reply.sender_id:
                        try:
                            reply_sender = await get_cached_entity(
                                client, reply.sender_id, "user"
                            )
                            if isinstance(reply_sender, TgUser):
                                reply_user_id = await fetch_and_save_full_user(
                                    client,
                                    session,
                                    telegram_user_model,
                                    reply_sender,
                                    media_dir=self.channel_media_dir,
                                )
                                reply_username = getattr(reply_sender, "username", None)
                                reply_first_name = getattr(
                                    reply_sender, "first_name", None
                                )
                                reply_last_name = getattr(
                                    reply_sender, "last_name", None
                                )
                        except (ValueError, TypeError) as e:
                            self.log_callback(
                                f"Error getting sender for reply {reply.id}: {e}"
                            )

                    if not reply_user_id and reply.sender_id:
                        reply_user_id = reply.sender_id

                    if reply_user_id:
                        if (
                            isinstance(reply_user_id, int)
                            and reply_user_id < 0
                            and str(reply_user_id).startswith("-100")
                        ):
                            pass
                        else:
                            await save_discussion_participant(
                                session,
                                member_model,
                                telegram_user_model,
                                channel_model,
                                reply_user_id,
                                channel_id,
                                username=reply_username,
                                first_name=reply_first_name,
                                last_name=reply_last_name,
                                member_type="discussion_author",
                            )

                    reply_to_id = None
                    if hasattr(reply, "reply_to") and reply.reply_to:
                        reply_to_id = reply.reply_to.reply_to_msg_id

                    existing_reply = get_existing_discussion(
                        session, discussion_model, reply.id, channel_id
                    )
                    if existing_reply:
                        reply_counter += 1
                        continue

                    add_discussion(
                        session,
                        discussion_model,
                        channel_id,
                        message_id=reply.id,
                        post_id=message.id,
                        text=reply.text,
                        date=reply.date,
                        user_id=reply_user_id,
                        media_path=reply_media_path,
                        reply_to_message_id=reply_to_id,
                    )

                    if collect_links and reply.text:
                        await self._process_links(
                            session, link_model, reply, message.id, channel_id
                        )

                    reply_counter += 1
                    if reply_counter % 5 == 0:
                        await safe_sleep(REPLY_DELAY)

                except FloodWaitError as e:
                    await handle_flood_wait(e)
                except Exception as e:
                    self.log_callback(
                        f"Error processing reply for message {message.id}: {e}"
                    )
                    await safe_sleep(REPLY_DELAY)
                    continue
        except Exception as e:
            self.log_callback(f"Error processing replies for message {message.id}: {e}")

    async def _download_discussion(self, client, message, discussion_dir, semaphore):
        async with semaphore:
            media_type, ext = self._get_media_info(message)
            if media_type:
                return await self._download_media_file(
                    client, message, media_type, ext, discussion_dir
                )
        return None

    async def _process_message(
        self,
        client,
        session,
        message,
        channel_media_dir,
        semaphore,
        entity,
        collect_links,
        link_model,
        telegram_user_model,
        post_model,
        discussion_model,
        member_model,
        channel_model,
        channel_id,
    ):
        media_path = await self._download_media_with_semaphore(
            message, client, channel_media_dir, semaphore
        )

        user_id = None
        username = None
        first_name = None
        last_name = None

        if message.sender_id:
            try:
                sender = await get_cached_entity(client, message.sender_id, "user")
                if isinstance(sender, TgUser):
                    user_id = await fetch_and_save_full_user(
                        client,
                        session,
                        telegram_user_model,
                        sender,
                        media_dir=self.channel_media_dir,
                    )
                    username = getattr(sender, "username", None)
                    first_name = getattr(sender, "first_name", None)
                    last_name = getattr(sender, "last_name", None)
            except (ValueError, TypeError) as e:
                self.log_callback(f"Error getting sender for message {message.id}: {e}")

        if user_id is None and entity:
            user_id = getattr(entity, "id", None)

        if user_id:
            try:
                await save_discussion_participant(
                    session,
                    member_model,
                    telegram_user_model,
                    channel_model,
                    user_id,
                    channel_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    member_type="member",
                )
            except Exception:
                pass

        is_forwarded = False
        forwarded_from_id = None
        forwarded_from_name = None
        if hasattr(message, "fwd_from") and message.fwd_from:
            is_forwarded = True
            fwd_from = message.fwd_from
            if hasattr(fwd_from, "from_id") and fwd_from.from_id:
                forwarded_from_id = getattr(
                    fwd_from.from_id, "user_id", None
                ) or getattr(fwd_from.from_id, "channel_id", None)
            if hasattr(fwd_from, "from_name") and fwd_from.from_name:
                forwarded_from_name = fwd_from.from_name
            elif getattr(fwd_from, "from", None):
                forwarded_from_name = getattr(fwd_from, "from", None)

        existing_post = get_existing_post(session, post_model, message.id, channel_id)
        if existing_post:
            return

        add_post(
            session,
            post_model,
            channel_id,
            post_id=message.id,
            text=message.text,
            media_path=media_path,
            date=message.date,
            views=message.views,
            forwards=message.forwards,
            user_id=user_id,
            is_forwarded=is_forwarded,
            forwarded_from_id=forwarded_from_id,
            forwarded_from_name=forwarded_from_name,
        )

        if collect_links and message.text:
            await self._process_links(session, link_model, message, None, channel_id)

        await self._process_discussion_replies(
            client,
            session,
            message,
            channel_media_dir,
            semaphore,
            entity,
            link_model,
            collect_links,
            telegram_user_model,
            discussion_model,
            member_model,
            channel_model,
            channel_id,
        )

        self.state.request_counter += 1

    async def _fetch_discussion_messages(
        self,
        client,
        session,
        discussion_chat,
        channel_media_dir,
        semaphore,
        collect_links,
        link_model,
        telegram_user_model,
        discussion_model,
        member_model,
        channel_model,
        post_model,
        channel_id,
    ):
        self.log_callback(
            f"Fetching messages from discussion chat: {getattr(discussion_chat, 'title', 'Unknown')}"
        )

        try:
            total_discussion = (
                await client.get_messages(discussion_chat, limit=0)
            ).total
        except Exception as e:
            self.log_callback(f"Could not get total discussion count: {e}")
            total_discussion = None

        limit = 100
        offset_id = 0
        message_counter = 0
        processed = 0

        while True:
            try:
                messages = await client.get_messages(
                    discussion_chat, limit=limit, offset_id=offset_id, reverse=False
                )
                if not messages:
                    break

                for msg in messages:
                    try:
                        reply_to_id = None
                        if hasattr(msg, "reply_to") and msg.reply_to:
                            reply_to_id = msg.reply_to.reply_to_msg_id

                        post_id = msg.reply_to_msg_id

                        if post_id:
                            existing_post = get_existing_post(
                                session, post_model, post_id, channel_id
                            )
                            if not existing_post:
                                add_post(
                                    session,
                                    post_model,
                                    channel_id,
                                    post_id=post_id,
                                    text=None,
                                    media_path=None,
                                    date=None,
                                    views=None,
                                    forwards=None,
                                    user_id=None,
                                    is_forwarded=False,
                                    forwarded_from_id=None,
                                    forwarded_from_name=None,
                                )

                        existing_discussion = get_existing_discussion(
                            session, discussion_model, msg.id, channel_id
                        )
                        if existing_discussion:
                            processed += 1
                            continue

                        media_path = await self._download_discussion(
                            client, msg, channel_media_dir, semaphore
                        )

                        user_id = None
                        username = None
                        first_name = None
                        last_name = None
                        if msg.sender_id:
                            try:
                                sender = await get_cached_entity(
                                    client, msg.sender_id, "user"
                                )
                                if isinstance(sender, TgUser):
                                    user_id = await fetch_and_save_full_user(
                                        client,
                                        session,
                                        telegram_user_model,
                                        sender,
                                        media_dir=self.channel_media_dir,
                                    )
                                    username = getattr(sender, "username", None)
                                    first_name = getattr(sender, "first_name", None)
                                    last_name = getattr(sender, "last_name", None)
                            except Exception as e:
                                self.log_callback(
                                    f"Error getting sender for discussion message {msg.id}: {e}"
                                )

                        if not user_id and msg.sender_id:
                            user_id = msg.sender_id

                        if user_id:
                            if (
                                isinstance(user_id, int)
                                and user_id < 0
                                and str(user_id).startswith("-100")
                            ):
                                pass
                            else:
                                await save_discussion_participant(
                                    session,
                                    member_model,
                                    telegram_user_model,
                                    channel_model,
                                    user_id,
                                    channel_id,
                                    username=username,
                                    first_name=first_name,
                                    last_name=last_name,
                                    member_type="discussion_author",
                                )

                        add_discussion(
                            session,
                            discussion_model,
                            channel_id,
                            message_id=msg.id,
                            post_id=post_id,
                            text=msg.text,
                            date=msg.date,
                            user_id=user_id,
                            media_path=media_path,
                            reply_to_message_id=reply_to_id,
                        )

                        if collect_links and msg.text:
                            await self._process_links(
                                session, link_model, msg, post_id, channel_id
                            )

                        processed += 1
                        message_counter += 1

                        if message_counter % 5 == 0:
                            await safe_sleep(REPLY_DELAY)

                    except FloodWaitError as e:
                        wait_time = e.seconds + 5
                        self.log_callback(
                            f"FloodWait while processing msg {msg.id}. Waiting {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                    except Exception as e:
                        self.log_callback(
                            f"Error processing discussion message {msg.id}: {e}"
                        )
                        await safe_sleep(REPLY_DELAY)
                        continue

                offset_id = messages[-1].id - 1

            except FloodWaitError as e:
                wait_time = e.seconds + 5
                self.log_callback(
                    f"FloodWait fetching discussion. Waiting {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
                continue
            except Exception as e:
                self.log_callback(f"Error fetching discussion messages: {e}")
                await safe_sleep(5.0)
                continue

        self.log_callback(f"Loaded {processed} discussion messages")
