from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.email_header_analyzer import EmailHeaderAnalyzer
    from src.modules.mail_search_engine import MailSearchEngine


class MailController:
    def __init__(
        self,
        ui: "QMainWindow",
        mail_search_engine: "MailSearchEngine",
        header_analyzer: "EmailHeaderAnalyzer | None" = None,
    ):
        logger.debug("Init: MailController")

        self.ui = ui
        self.mail_search_engine = mail_search_engine
        if header_analyzer is None:
            from src.modules.email_header_analyzer import EmailHeaderAnalyzer

            header_analyzer = EmailHeaderAnalyzer()
        self.header_analyzer = header_analyzer

    async def start_intelx_search(self, email):
        self.ui.mailSearchDebug.setPlainText(
            await self.mail_search_engine.get_data(email)
        )

    async def start_hibp_check(self, email):
        self.ui.hibpDebug.setPlainText(await self.mail_search_engine.check_hibp(email))

    def _eml_debug_widget(self):
        return getattr(self.ui, "emailHeaderDebug", None) or self.ui.mailSearchDebug

    async def analyze_eml_file(self, path: str):
        widget = self._eml_debug_widget()
        widget.setPlainText("Analyzing email headers...")
        widget.setPlainText(await self.header_analyzer.analyze_file(path))

    async def analyze_headers_text(self, raw_headers: str):
        widget = self._eml_debug_widget()
        widget.setPlainText("Analyzing email headers...")
        widget.setPlainText(await self.header_analyzer.analyze_text(raw_headers))
