from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.maigret_search import MaigretSearch
    from src.modules.username_search import UsernameSearch


class UsernameController:
    def __init__(
        self,
        ui: "QMainWindow",
        username_search: "UsernameSearch",
        maigret_search: "MaigretSearch",
    ):
        logger.debug("Init: UsernameController")

        self.ui = ui
        self.username_search = username_search
        self.maigret_search = maigret_search

    async def start_searching(self, username):
        self.ui.usernameScriptDebug.clear()
        self.ui.maigretDebug.clear()
        self.ui.usernameSearchProgress.setValue(0)

        try:
            maigret_report = await self.maigret_search.search_and_report(
                username,
                on_progress=lambda done, total: (
                    self.ui.usernameSearchProgress.setRange(0, total),
                    self.ui.usernameSearchProgress.setValue(done),
                ),
            )
            self.ui.maigretDebug.setPlainText(maigret_report)

            results = await self.username_search.acheck(
                username,
                on_result=lambda r: self.ui.usernameScriptDebug.appendPlainText(
                    f"[{r['status']}] {r['site']}: {r['url_user']}"
                ),
                on_progress=lambda done, total: (
                    self.ui.usernameSearchProgress.setRange(0, total),
                    self.ui.usernameSearchProgress.setValue(done),
                ),
            )

            found = sum(1 for r in results if r["status"] == "Claimed")
            self.ui.usernameScriptDebug.appendPlainText(
                f"\n--- Search completed: {found} found ---"
            )
        except Exception as e:
            self.ui.usernameScriptDebug.appendPlainText(f"\n--- Error: {e} ---")
