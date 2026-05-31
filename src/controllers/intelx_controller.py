from typing import TYPE_CHECKING

from loguru import logger

from src.thread_utils import invoke

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.intelx_search_engine import IntelxSearchEngine


class IntelxController:
    def __init__(
        self,
        ui: "QMainWindow",
        intelx_search_engine: "IntelxSearchEngine",
    ):
        logger.debug("Init: IntelxController")

        self.ui = ui
        self.intelx_search_engine = intelx_search_engine

    def start_searching(self, email):
        invoke(
            self.ui.mailSearchDebug,
            "setPlainText",
            self.intelx_search_engine.get_data(email),
        )
