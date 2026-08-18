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
        ui: QMainWindow,
        tg_downloader: TgDownloader,
        proxy: Proxy | None = None,
        case_manager=None,
        file_analyzer: object | None = None,
    ):
        logger.debug("Init: TgDownloaderController")

        self.ui = ui
        self.tg_downloader = tg_downloader
        self.proxy = proxy
        self.case_manager = case_manager
        self.file_analyzer = file_analyzer
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
        safe_config = {k: v for k, v in config.items() if k != "api_hash"}
        logger.debug("start_collection: config={}", safe_config)
        self.ui.telegramDownloaderDebug.clear()
        self.ui.telegramDownloadProgress.setValue(0)
        self.ui.current_stage = None

        downloader = self.tg_downloader.__class__(
            config,
            log_callback=lambda msg: self._bridge.log_signal.emit(_strip_ansi(msg)),
            progress_callback=lambda val: self._bridge.progress_signal.emit(val),
            file_analyzer=self.file_analyzer,
        )

        loop = asyncio.get_running_loop()
        self._task = loop.run_in_executor(None, lambda: asyncio.run(downloader.run()))
        try:
            await self._task
            logger.debug("start_collection: finished successfully")
            self._bridge.finished_signal.emit()
            phone = getattr(downloader, "account_phone", None)
            logger.debug("start_collection: phone_available={}", bool(phone))
            if phone:
                self.ui.telegramAccountInfo.setText(phone)
        except Exception as e:
            logger.error("start_collection: exception: {}", e)
            self._bridge.log_signal.emit(f"Error: {e}")

    async def start_avatar_download(self):
        config = self.build_collection_config()
        logger.debug("start_avatar_download: path={}", config.get("path"))
        self.ui.telegramDownloaderDebug.clear()
        self.ui.telegramDownloadProgress.setValue(0)

        downloader = self.tg_downloader.__class__(
            config,
            log_callback=lambda msg: self._bridge.log_signal.emit(_strip_ansi(msg)),
            progress_callback=lambda val: self._bridge.progress_signal.emit(val),
            file_analyzer=self.file_analyzer,
        )

        loop = asyncio.get_running_loop()
        self._task = loop.run_in_executor(
            None, lambda: asyncio.run(downloader.download_avatars())
        )
        try:
            await self._task
            logger.debug("start_avatar_download: finished successfully")
            self._bridge.finished_signal.emit()
        except Exception as e:
            logger.error("start_avatar_download: exception: {}", e)
            self._bridge.log_signal.emit(f"Error: {e}")

    def _handle_progress(self, value):
        if isinstance(value, tuple):
            stage, progress = value
            logger.debug("_handle_progress: stage={}, progress={}", stage, progress)
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

        default_path = str(Path.home() / ".skyfall" / "data")
        tg_data_path = (
            str(self.case_manager.current_case_path / "telegram")
            if self.case_manager and self.case_manager.current_case_path
            else default_path
        )
        return {
            "api_id": self.ui.tgApiKeyEdit.text(),
            "api_hash": self.ui.telegramApiHashEdit.text(),
            "channel": self.ui.telegramUsernameEdit.text(),
            "path": tg_data_path,
            "session_path": default_path,
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
                self.proxy.get_proxy_url()
                if self.proxy
                else self.ui.proxyListEdit.toPlainText()
            ),
        }
