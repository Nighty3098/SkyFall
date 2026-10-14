from typing import TYPE_CHECKING

from loguru import logger

from src.ui.output_formatter import render

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.email_accounts import EmailAccounts
    from src.modules.email_header_analyzer import EmailHeaderAnalyzer
    from src.modules.mail_search_engine import MailSearchEngine


class MailController:
    def __init__(
        self,
        ui: "QMainWindow",
        mail_search_engine: "MailSearchEngine",
        header_analyzer: "EmailHeaderAnalyzer | None" = None,
        email_accounts: "EmailAccounts | None" = None,
    ):
        logger.debug("Init: MailController")

        self.ui = ui
        self.mail_search_engine = mail_search_engine
        if header_analyzer is None:
            from src.modules.email_header_analyzer import EmailHeaderAnalyzer

            header_analyzer = EmailHeaderAnalyzer()
        self.header_analyzer = header_analyzer
        if email_accounts is None:
            from src.modules.email_accounts import EmailAccounts

            email_accounts = EmailAccounts()
        self.email_accounts = email_accounts

    async def start_intelx_search(self, email):
        result = await self.mail_search_engine.get_data(email)
        self.ui.mailSearchDebug.setPlainText(render(result, title=f"IntelX: {email}"))

    async def start_hibp_check(self, email):
        result = await self.mail_search_engine.check_hibp(email)
        self.ui.hibpDebug.setPlainText(render(result, title=f"HIBP: {email}"))

    async def check_accounts(self, email):
        widget = getattr(self.ui, "emailAccountsDebug", None) or self.ui.mailSearchDebug
        widget.setPlainText("Checking registered accounts...")
        result = await self.email_accounts.check(email)
        widget.setPlainText(render(result, title=f"Registered accounts: {email}"))

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
