from typing import TYPE_CHECKING

from loguru import logger

from src.modules.username_merge import merge_sources, report
from src.modules.username_search import UsernameSearch
from src.ui.output_formatter import error, render

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.maigret_search import MaigretSearch
    from src.modules.username_search import UsernameSearch as UsernameSearchType


class UsernameController:
    def __init__(
        self,
        ui: "QMainWindow",
        username_search: "UsernameSearchType",
        maigret_search: "MaigretSearch",
        proxy=None,
    ):
        logger.debug("Init: UsernameController")

        self.ui = ui
        self.username_search = username_search
        self.maigret_search = maigret_search
        self.proxy = proxy

    def _set_status(self, text: str):
        field = getattr(self.ui, "usernameResultsDebug", None)
        if field is not None:
            field.setPlainText(text)

    def _on_progress(self, done: int, total: int):
        self.ui.usernameSearchProgress.setRange(0, total)
        self.ui.usernameSearchProgress.setValue(done)

    async def start_searching(self, username):
        username = (username or "").strip()
        if not username:
            self._set_status(error("Enter a username first"))
            return

        self._set_status(f"Searching Maigret for {username}…")
        self.ui.usernameSearchProgress.setValue(0)

        try:
            maigret_report, maigret_matches = (
                await self.maigret_search.search_and_report_structured(
                    username, on_progress=self._on_progress
                )
            )

            self._set_status(
                f"Maigret found {len(maigret_matches)} account(s) "
                f"for {username}, running Sherlock…"
            )
            results = await self.username_search.acheck(
                username,
                proxy=(self.proxy.get_proxy_url() if self.proxy else None),
                on_progress=self._on_progress,
            )

            claimed = UsernameSearch.Status.CLAIMED
            sherlock_found = [r for r in results if r["status"] == claimed]

            confirmed, sherlock_only, maigret_only = merge_sources(
                sherlock_found, maigret_matches
            )
            report_data = report(username, confirmed, sherlock_only, maigret_only)
            if maigret_report.get("error"):
                report_data["Maigret error"] = maigret_report["error"]
            self._set_status(
                render(
                    report_data,
                    title=f"Username OSINT: {username}",
                )
            )
        except Exception as e:
            logger.exception("Username search failed")
            self._set_status(error(f"Error: {e}"))
