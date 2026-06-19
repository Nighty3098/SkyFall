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
        self.ui.usernameSearchProgress.setValue(0)

        results = await self.username_search.check_async(
            username,
            on_result=lambda r: self.ui.usernameScriptDebug.appendPlainText(
                f"[{r['status']}] {r['site']}: {r['url_user']}"
            ),
            on_progress=lambda done, total: (
                self.ui.usernameSearchProgress.setRange(0, total),
                self.ui.usernameSearchProgress.setValue(done),
            ),
        )

        self.ui.usernameScriptDebug.appendPlainText(
            f"\n--- Search completed: {sum(1 for r in results if r['status'] == 'Claimed')} found ---"  # noqa: E501
        )
