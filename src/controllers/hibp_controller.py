from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow
    from src.modules.hibp_search import HibpSearch


class HibpController:
    def __init__(
        self,
        ui: "QMainWindow",
        hibp_search: "HibpSearch",
    ):
        logger.debug("Init: HibpController")
        self.ui = ui
        self.hibp_search = hibp_search

    async def start_searching(self, email):
        self.ui.hibpDebug.setPlainText(
            await self.hibp_search.get_data(email)
        )
