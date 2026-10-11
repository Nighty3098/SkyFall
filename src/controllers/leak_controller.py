from typing import TYPE_CHECKING

from loguru import logger

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
        widget.setPlainText(await self.leak_search.check(target, self.keys))

    async def infostealer(self, target=None):
        widget = self._debug()
        if widget is None:
            return
        target = target or self._target()
        widget.setPlainText("Searching infostealer logs (Hudson Rock)...")
        data = await self.leak_search.infostealer(target)
        lines = [f"[+] Infostealer logs: {target}"]
        lines += self.leak_search._render_infostealer(data)
        widget.setPlainText("\n".join(lines))

    async def leakcheck(self, target=None):
        widget = self._debug()
        if widget is None:
            return
        target = target or self._target()
        widget.setPlainText("Searching LeakCheck...")
        data = await self.leak_search.leakcheck(
            target, self.keys.get("leakcheck_api_key", "")
        )
        lines = [f"[+] LeakCheck: {target}"]
        lines += self.leak_search._render_leakcheck(data)
        widget.setPlainText("\n".join(lines))

    async def hibp(self, target=None):
        widget = self._debug()
        if widget is None:
            return
        target = target or self._target()
        widget.setPlainText("Checking Have I Been Pwned...")
        data = await self.leak_search.hibp(target, self.keys.get("hibp_api_key", ""))
        lines = [f"[+] HIBP: {target}"]
        lines += self.leak_search._render_hibp(data)
        widget.setPlainText("\n".join(lines))

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
        lines = [f"[+] Dehashed: {target}"]
        lines += self.leak_search._render_dehashed(data)
        widget.setPlainText("\n".join(lines))
