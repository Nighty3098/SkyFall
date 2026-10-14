from typing import TYPE_CHECKING

from loguru import logger

from src.ui.output_formatter import render

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.archive_search import ArchiveSearch


class ArchiveController:
    def __init__(self, ui: "QMainWindow", archive: "ArchiveSearch"):
        logger.debug("Init: ArchiveController")
        self.ui = ui
        self.archive = archive

    def _url(self) -> str:
        widget = getattr(self.ui, "archiveUrlEdit", None)
        return widget.text().strip() if widget is not None else ""

    def _debug(self):
        return getattr(self.ui, "archiveDebug", None)

    async def check(self, url=None):
        widget = self._debug()
        if widget is None:
            return
        url = url or self._url()
        widget.setPlainText("Checking archives...")
        data = await self.archive.check(url)
        widget.setPlainText(render(data, f"Archive: {url}"))

    async def availability(self, url=None):
        widget = self._debug()
        if widget is None:
            return
        url = url or self._url()
        widget.setPlainText("Checking the Wayback Machine...")
        data = await self.archive.availability(url)
        widget.setPlainText(render(data, "Wayback Machine"))

    async def snapshots(self, url=None):
        widget = self._debug()
        if widget is None:
            return
        url = url or self._url()
        widget.setPlainText("Listing Wayback snapshots...")
        data = await self.archive.snapshots(url)
        widget.setPlainText(render(data, "Wayback snapshots"))

    async def save(self, url=None):
        widget = self._debug()
        if widget is None:
            return
        url = url or self._url()
        widget.setPlainText("Saving to the Wayback Machine (this may take a while)...")
        data = await self.archive.save(url)
        widget.setPlainText(render(data, "Wayback save"))

    async def archive_today(self, url=None):
        widget = self._debug()
        if widget is None:
            return
        url = url or self._url()
        widget.setPlainText("Checking archive.today...")
        data = await self.archive.archive_today(url)
        widget.setPlainText(render(data, "archive.today"))
