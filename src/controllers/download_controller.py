from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger
from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QDesktopServices

from src.ui.output_formatter import divider, end_of, error, info, title

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.controllers.proxy_controller import Proxy
    from src.modules.downloader import DownloadManager


class _DownloadBridge(QObject):
    log_signal = Signal(str)
    progress_signal = Signal(object)
    finished_signal = Signal(str)


class DownloadController:
    def __init__(
        self,
        ui: QMainWindow,
        download_manager: DownloadManager,
        settings=None,
        case_manager=None,
        proxy: Proxy | None = None,
    ):
        logger.debug("Init: DownloadController")

        self.ui = ui
        self.download_manager = download_manager
        self.settings = settings
        self.case_manager = case_manager
        self.proxy = proxy

        self._last_download: str | None = None

        self._bridge = _DownloadBridge()
        self._bridge.log_signal.connect(self._append_log)
        self._bridge.progress_signal.connect(self._handle_progress)
        self._bridge.finished_signal.connect(self._on_finished)

    async def start_download(self):
        url = self.ui.linkToDownloadEdit.text().strip()
        if not url:
            self.ui.downloadFileDebug.appendPlainText(error("Link is empty"))
            logger.warning("start_download: empty link")
            return

        logger.debug("start_download: url={}", url)
        self.ui.downloadFileDebug.clear()
        bar = self.ui.downloadFromLinkProgress
        bar.setRange(0, 100)
        bar.setValue(0)

        self._append_log(title("Download"))
        self._append_log(divider())

        dest_dir = self._get_download_dir()
        self._append_log(info(f"Target directory: {dest_dir}"))

        proxy_url = None
        if self.ui.useProxyToDownloadCheck.isChecked():
            proxy_url = self._get_proxy()
            if not proxy_url:
                self._append_log(
                    error("Proxy is enabled, but no proxies found in settings")
                )
                return

        try:
            result_path = await self.download_manager.download(
                url,
                dest_dir,
                proxy=proxy_url,
                log_callback=self._bridge.log_signal.emit,
                progress_callback=self._bridge.progress_signal.emit,
            )
            self._bridge.finished_signal.emit(result_path)
        except Exception as e:
            logger.error("start_download: exception: {}", e)
            self._append_log(error(str(e)))
            bar.setRange(0, 100)
            bar.setValue(0)

    def _get_download_dir(self) -> str:
        if self.case_manager and self.case_manager.current_case_path:
            return self.case_manager.get_downloads_dir()

        if self.settings and self.settings.path_to_storage:
            path = Path(self.settings.path_to_storage)
            path.mkdir(parents=True, exist_ok=True)
            return str(path)

        fallback = Path.home() / ".skyfall" / "data" / "downloads"
        fallback.mkdir(parents=True, exist_ok=True)
        return str(fallback)

    def _get_proxy(self) -> str | None:
        if self.proxy:
            return self.proxy.get_proxy_url()
        for line in self.ui.proxyListEdit.toPlainText().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line
        return None

    def _append_log(self, message: str):
        self.ui.downloadFileDebug.appendPlainText(message)

    def _handle_progress(self, value):
        bar = self.ui.downloadFromLinkProgress
        if value is None:
            bar.setRange(0, 0)
            return
        percent, downloaded, total = value
        if bar.maximum() == 0:
            bar.setRange(0, 100)
        if percent is None:
            return
        bar.setValue(percent)
        if percent in (25, 50, 75):
            self._append_log(info(f"Progress: {percent}% ({downloaded} bytes)"))
        elif percent == 100 and total is not None:
            self._append_log(info(f"Progress: 100% ({downloaded} bytes)"))

    def _on_finished(self, result_path: str):
        self._last_download = result_path
        bar = self.ui.downloadFromLinkProgress
        bar.setRange(0, 100)
        bar.setValue(100)
        self._append_log(info(f"Done: {result_path}"))
        self._append_log(divider())
        self._append_log(end_of("Download"))

    def open_last_downloaded(self):
        if not self._last_download:
            self.ui.downloadFileDebug.appendPlainText(error("Nothing downloaded yet"))
            return
        path = Path(self._last_download)
        if not path.exists():
            self.ui.downloadFileDebug.appendPlainText(error(f"File not found: {path}"))
            return
        logger.debug("open_last_downloaded: path={}", path)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
