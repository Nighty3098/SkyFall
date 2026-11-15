from __future__ import annotations

import re
import asyncio
import os
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFileDialog

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.tg_osint import TgOSINT

class TgOSINTController:
    def __init__(
        self,
        ui: QMainWindow,
        tg_osint: TgOSINT,
        graph_widget=None,
        proxy=None,
    ):
        logger.debug("Init: TgOSINTController")

        self.ui = ui
        self.tg_osint = tg_osint
        self.proxy = proxy
        self.osint_input = self.ui.tgOsintEdit
        self.osint_debug = self.ui.telegramOsintDebug
        self._busy = False
        self._USER_ID_RE = re.compile(r"-?(?:100)?\d{5,16}")
        self._USERNAME_RE = re.compile(
            r"(?:@|(?:(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me|telegram\.dog)/)"
            r"|tg://resolve\?domain=)?([A-Za-z][A-Za-z0-9_]{3,31})",
            re.IGNORECASE,
        )
        self._BOT_TOKEN_RE = re.compile(r"\d{5,16}:[A-Za-z0-9_-]{30,}")


    def detect_id_type(self, value: str) -> int | None:
        """
        Returns:
            0 - user_id (marked: -100...),
            1 - username ('@name', 'name', 't.me/name', 'tg://resolve?domain=name'),
            2 - bot token,
            None
        """
        if not isinstance(value, str):
            return None
        s = value.strip()

        if self._BOT_TOKEN_RE.fullmatch(s):
            return 2
        if self._USER_ID_RE.fullmatch(s):
            return 0
        if self._USERNAME_RE.fullmatch(s):
            return 1
        return None

    async def analyze(self):
        if self._busy:
            return
        self._busy = True

        run_button = getattr(self.ui, "runTgOsintButton", None)
        if run_button is not None:
            run_button.setEnabled(False)

        try:
            await self._analyze()
        finally:
            self._busy = False
            if run_button is not None:
                run_button.setEnabled(True)

    async def _analyze(self):
        raw = self.osint_input.text().strip()
        self.osint_debug.clear()

        if not raw:
            self.osint_debug.appendPlainText(
                "Enter a Telegram user ID, @username, or bot token."
            )
            return

        id_type = self.detect_id_type(raw)
        if id_type is None:
            self.osint_debug.appendPlainText(f"Unrecognized input: {raw!r}")
            return

        def log(message: str):
            logger.info(message)
            self.osint_debug.appendPlainText(message)

        try:
            if self.proxy is not None:
                proxy_url = self.proxy.get_proxy_url()
                if not proxy_url:
                    proxy_url = self.proxy.get_first_proxy()
                self.tg_osint.set_proxy(proxy_url, use_proxy=bool(proxy_url))
                log(f"Proxy: {'enabled' if proxy_url else 'disabled'}")

            if id_type == 0:
                peer_id = int(raw)
                log(f"Resolving @username for id {peer_id}...")
                username = await self.tg_osint.get_username_by_id(peer_id)
                if username:
                    log(f"id {peer_id} -> @{username}")
                else:
                    log(f"No public username found for id {peer_id}")

            elif id_type == 1:
                match = self._USERNAME_RE.fullmatch(raw)
                username = match.group(1) if match else raw
                log(f"Resolving id for @{username}...")
                raw_id = await self.tg_osint.get_id_by_username(username, marked=False)
                if raw_id is None:
                    log(f"Could not resolve @{username}")
                    return
                marked_id = await self.tg_osint.get_id_by_username(
                    username, marked=True
                )
                log(f"@{username} -> id={raw_id}, marked_id={marked_id}")

            elif id_type == 2:
                log("Checking bot token...")
                username = await self.tg_osint.get_username_by_bot_token(raw)
                if username:
                    log(f"Bot token is valid: @{username}")
                else:
                    log("Bot token is invalid or has no username")

            log("Done.")
        except Exception as e:
            logger.error("TG OSINT analyze failed: {}", e)
            log(f"Error: {e}")
