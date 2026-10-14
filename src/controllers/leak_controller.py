from typing import TYPE_CHECKING

from loguru import logger

from src.ui.output_formatter import render

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.leak_search import LeakSearch


class LeakController:
    def __init__(
        self,
        ui: "QMainWindow",
        leak_search: "LeakSearch",
        keys: dict | None = None,
    ):
        logger.debug("Init: LeakController")
        self.ui = ui
        self.leak_search = leak_search
        self.keys = keys or {}

    def _target(self) -> str:
        widget = getattr(self.ui, "leakTargetEdit", None)
        return widget.text().strip() if widget is not None else ""

    def _debug(self):
        return getattr(self.ui, "leakDebug", None)

    async def search_all(self, target=None):
        widget = self._debug()
        if widget is None:
            return
        target = target or self._target()
        widget.setPlainText("Searching leaks and infostealer logs...")
        data = await self.leak_search.check(target, self.keys)
        widget.setPlainText(render(data, f"Leak search: {target}"))

    async def infostealer(self, target=None):
        widget = self._debug()
        if widget is None:
            return
        target = target or self._target()
        widget.setPlainText("Searching infostealer logs (Hudson Rock)...")
        data = await self.leak_search.infostealer(target)
        summary = self.leak_search.summarize_infostealer(data)
        widget.setPlainText(render(summary, f"Infostealer logs: {target}"))

    async def leakcheck(self, target=None):
        widget = self._debug()
        if widget is None:
            return
        target = target or self._target()
        widget.setPlainText("Searching LeakCheck...")
        data = await self.leak_search.leakcheck(
            target, self.keys.get("leakcheck_api_key", "")
        )
        summary = self.leak_search.summarize_leakcheck(data)
        widget.setPlainText(render(summary, f"LeakCheck: {target}"))

    async def hibp(self, target=None):
        widget = self._debug()
        if widget is None:
            return
        target = target or self._target()
        widget.setPlainText("Checking Have I Been Pwned...")
        data = await self.leak_search.hibp(target, self.keys.get("hibp_api_key", ""))
        summary = self.leak_search.summarize_hibp(data)
        widget.setPlainText(render(summary, f"HIBP: {target}"))

    async def dehashed(self, target=None):
        widget = self._debug()
        if widget is None:
            return
        target = target or self._target()
        widget.setPlainText("Searching Dehashed...")
        data = await self.leak_search.dehashed(
            target,
            self.keys.get("dehashed_email", ""),
            self.keys.get("dehashed_api_key", ""),
        )
        summary = self.leak_search.summarize_dehashed(data)
        widget.setPlainText(render(summary, f"Dehashed: {target}"))
