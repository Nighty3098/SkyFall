import asyncio
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.username_search import UsernameSearch


class UsernameController:
    def __init__(
        self,
        ui: "QMainWindow",
        username_search: "UsernameSearch",
    ):
        logger.debug("Init: UsernameController")

        self.ui = ui
        self.username_search = username_search

    async def start_searching(self, username):
        self.ui.usernameScriptDebug.clear()
        self.ui.usernameSearchProgress.setRange(0, 0)

        results = await asyncio.to_thread(self.username_search.check, username)

        lines = "\n".join(
            f"[{r['status']}] {r['site']}: {r['url_user'] or 'N/A'}"
            for r in results
        )
        found = sum(1 for r in results if r["status"] == "Claimed")
        self.ui.usernameScriptDebug.setPlainText(
            f"{lines}\n\n--- Search completed: {found} found ---"
        )
        self.ui.usernameSearchProgress.setRange(0, 100)
        self.ui.usernameSearchProgress.setValue(100)
