from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger
from PySide6.QtCore import QObject, Signal

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.tg_analyzer import TgAnalyzer


class _AnalyzerBridge(QObject):
    log_signal = Signal(str)
    progress_signal = Signal(int)
    finished_signal = Signal()


class TgAnalyzerController:
    def __init__(self, ui: QMainWindow, tg_analyzer: TgAnalyzer):
        logger.debug("Init: TgAnalyzerController")

        self.ui = ui
        self.tg_analyzer = tg_analyzer
        self._task = None
        self._bridge = _AnalyzerBridge()
        self._bridge.log_signal.connect(self.ui.telegramAnalyzerDebug.appendPlainText)
        self._bridge.progress_signal.connect(self.ui.telegramAnalyzerProgress.setValue)
        self._bridge.finished_signal.connect(
            lambda: self.ui.telegramAnalyzerDebug.appendPlainText("Analysis completed.")
        )

    def load_channels(self, db_path: str):
        logger.debug("load_channels: raw db_path='{}'", db_path)
        if not db_path:
            db_path = str(Path.home() / ".skyfall" / "data")
            logger.debug("load_channels: using default path '{}'", db_path)

        if not os.path.exists(db_path):
            logger.warning("load_channels: path does not exist: '{}'", db_path)
            return False, "Database file not found"

        resolved = db_path
        if os.path.isdir(db_path):
            resolved = os.path.join(db_path, "SkyFall_TG.db")
            logger.debug("load_channels: resolved dir to file: '{}'", resolved)

        if not os.path.exists(resolved):
            logger.warning(
                "load_channels: DB file does not exist: '{}'. "
                "Run TG downloader first to create the database.",
                resolved,
            )
            return False, f"Database file not found: {resolved}"

        try:
            channels = self.tg_analyzer.get_channels(db_path)
            logger.debug("load_channels: got {} channels", len(channels))
            self.ui.telegramChannelsList.clear()
            self.ui.telegramChannelsList.addItems(channels)
            self.ui.telegramChannelsList.addItem("All Channels")
            logger.debug("load_channels: added {} items to list", len(channels) + 1)
            return True, None
        except Exception as e:
            logger.error("load_channels: exception: {}", e)
            return False, str(e)

    def build_analysis_params(self) -> dict:
        from pathlib import Path

        db_path = str(Path.home() / ".skyfall" / "data")

        selected_channels = [
            item.text() for item in self.ui.telegramChannelsList.selectedItems()
        ]
        loaded_channels = [
            self.ui.telegramChannelsList.item(i).text()
            for i in range(self.ui.telegramChannelsList.count())
        ]
        loaded_channels = [ch for ch in loaded_channels if ch != "All Channels"]

        start_date_str = self.ui.telegramAnalyzerStartDate.dateTime().toString(
            "yyyy-MM-dd"
        )
        end_date_str = self.ui.telegramAnalyzerEndDate.dateTime().toString("yyyy-MM-dd")
        if start_date_str == "2000-01-01" and end_date_str == "2000-01-01":
            start_date = None
            end_date = None
        else:
            start_date = start_date_str
            end_date = end_date_str

        params = {
            "db_path": db_path,
            "channels": (
                loaded_channels
                if "All Channels" in selected_channels
                else selected_channels
                if selected_channels
                else loaded_channels
            ),
            "min_replies": self.ui.telegramAnalyzerMinReplies.value(),
            "include_forwarded": self.ui.includeForwardingCheck.isChecked(),
            "include_links": self.ui.includeLinksCheck.isChecked(),
            "start_date": start_date,
            "end_date": end_date,
            "formats": [],
        }

        format_map = {
            self.ui.telegramAnalyzerGraphMLCheck: "graphml",
            self.ui.checkBox_7: "gexf",
            self.ui.telegramAnalyzerJSONCheck: "json",
            self.ui.telegramAnalyzerCSVCheck: "csv-nodes",
            self.ui.checkBox_8: "csv-edges",
            self.ui.telegramAnalyzerPNGCheck: "png",
            self.ui.telegramAnalyzerHTMLCheck: "html",
            self.ui.telegramAnalyzerObsidianCheck: "obsidian",
        }
        for widget, fmt in format_map.items():
            if widget.isChecked():
                params["formats"].append(fmt)

        return params

    async def run_analysis(self, params: dict):
        self.ui.telegramAnalyzerDebug.clear()
        self.ui.telegramAnalyzerProgress.setValue(0)

        self._task = asyncio.get_event_loop().run_in_executor(
            None,
            self.tg_analyzer.run_analysis,
            params,
            self._bridge.log_signal.emit,
            self._bridge.progress_signal.emit,
        )
        try:
            await self._task
            self._bridge.finished_signal.emit()
        except Exception as e:
            self.ui.telegramAnalyzerDebug.appendPlainText(f"Error: {e}")
