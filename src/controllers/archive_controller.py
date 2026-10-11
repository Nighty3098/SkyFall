from typing import TYPE_CHECKING

from loguru import logger

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
        widget.setPlainText(await self.archive.check(url))

    async def availability(self, url=None):
        widget = self._debug()
        if widget is None:
            return
        url = url or self._url()
        widget.setPlainText("Checking the Wayback Machine...")
        data = await self.archive.availability(url)
        widget.setPlainText(self.archive.render_availability(data))

    async def snapshots(self, url=None):
        widget = self._debug()
        if widget is None:
            return
        url = url or self._url()
        widget.setPlainText("Listing Wayback snapshots...")
        data = await self.archive.snapshots(url)
        widget.setPlainText(self.archive.render_snapshots(data))

    async def save(self, url=None):
        widget = self._debug()
        if widget is None:
            return
        url = url or self._url()
        widget.setPlainText("Saving to the Wayback Machine (this may take a while)...")
        data = await self.archive.save(url)
        widget.setPlainText(self.archive.render_save(data))

    async def archive_today(self, url=None):
        widget = self._debug()
        if widget is None:
            return
        url = url or self._url()
        widget.setPlainText("Checking archive.today...")
        data = await self.archive.archive_today(url)
        widget.setPlainText(self.archive.render_archive_today(data))
