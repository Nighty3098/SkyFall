from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING

from loguru import logger
from PySide6.QtCore import QObject, Signal

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.controllers.proxy_controller import Proxy
    from src.modules.tg_downloader import TgDownloader


def _strip_ansi(text):
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


class _DownloaderBridge(QObject):
    log_signal = Signal(str)
    progress_signal = Signal(object)
    finished_signal = Signal()


class TgDownloaderController:
    def __init__(
        self,
        ui: "QMainWindow",
        tg_downloader: "TgDownloader",
        proxy: "Proxy | None" = None,
    ):
        logger.debug("Init: TgDownloaderController")

        self.ui = ui
        self.tg_downloader = tg_downloader
        self.proxy = proxy
        self._task = None
        self._bridge = _DownloaderBridge()
        self._bridge.log_signal.connect(
            lambda msg: self.ui.telegramDownloaderDebug.appendPlainText(msg)
        )
        self._bridge.progress_signal.connect(self._handle_progress)
        self._bridge.finished_signal.connect(
            lambda: self.ui.telegramDownloaderDebug.appendPlainText(
                "Collection completed."
            )
        )

    async def start_collection(self, config: dict):
        self.ui.telegramDownloaderDebug.clear()
        self.ui.telegramDownloadProgress.setValue(0)
        self.ui.current_stage = None

        downloader = self.tg_downloader.__class__(
            config,
            log_callback=lambda msg: self._bridge.log_signal.emit(_strip_ansi(msg)),
            progress_callback=lambda val: self._bridge.progress_signal.emit(val),
        )

        loop = asyncio.get_running_loop()
        self._task = loop.run_in_executor(None, lambda: asyncio.run(downloader.run()))
        try:
            await self._task
            self._bridge.finished_signal.emit()
        except Exception as e:
            self._bridge.log_signal.emit(f"Error: {e}")

    def _handle_progress(self, value):
        if isinstance(value, tuple):
            stage, progress = value
            if stage == "done":
                self.ui.telegramDownloadProgress.setValue(100)
            elif stage != self.ui.current_stage:
                self.ui.current_stage = stage
                self.ui.telegramDownloadProgress.setValue(0)
                self.ui.telegramDownloadProgress.setValue(progress)
            else:
                self.ui.telegramDownloadProgress.setValue(progress)
        else:
            self.ui.telegramDownloadProgress.setValue(value)

    def build_collection_config(self) -> dict:
        from pathlib import Path
        tg_data_path = str(Path.home() / ".skyfall" / "data")
        return {
            "api_id": self.ui.tgApiKeyEdit.text(),
            "api_hash": self.ui.telegramApiHashEdit.text(),
            "channel": self.ui.telegramUsernameEdit.text(),
            "path": tg_data_path,
            "collect_members": self.ui.telegramCollectMembersCheck.isChecked(),
            "collect_links": self.ui.telegramCollectLinksCheck.isChecked(),
            "download_media": self.ui.telegramDownloadMediaCheck.isChecked(),
            "multi_acc": self.ui.telegramMultiAccCheck.isChecked(),
            "base_delay": self.ui.telegramBaseDelay.value(),
            "member_delay": self.ui.telegrammembersDelay.value(),
            "max_requests": self.ui.telegramMaxReq.value(),
            "pause_duration": self.ui.telegramPause.value(),
            "use_proxy": self.ui.telegramUseProxyCheck.isChecked(),
            "proxy_list": (
                self.proxy.get_proxies_text()
                if self.proxy
                else self.ui.proxyListEdit.toPlainText()
            ),
        }
