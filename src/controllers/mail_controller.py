from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.mail_search_engine import MailSearchEngine


class MailController:
    def __init__(
        self,
        ui: "QMainWindow",
        mail_search_engine: "MailSearchEngine",
    ):
        logger.debug("Init: MailController")

        self.ui = ui
        self.mail_search_engine = mail_search_engine

    async def start_intelx_search(self, email):
        self.ui.mailSearchDebug.setPlainText(
            await self.mail_search_engine.get_data(email)
        )

    async def start_hibp_check(self, email):
        self.ui.hibpDebug.setPlainText(
            await self.mail_search_engine.check_hibp(email)
        )
