from typing import TYPE_CHECKING

from loguru import logger

from src.thread_utils import invoke

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.dorks_search_engine import DorksSearchEngine
    from src.modules.google_dorks import GoogleDorksDB


class DorkingController:
    def __init__(
        self,
        ui: "QMainWindow",
        google_dorks_db: "GoogleDorksDB",
        dorks_search_engine: "DorksSearchEngine",
    ):
        logger.debug("Init: DorkingController")

        self.ui = ui
        self.google_dorks_db = google_dorks_db
        self.dorks_search_engine = dorks_search_engine

    def load_categories(self):
        categories = self.google_dorks_db.get_all_categories()
        for category in categories:
            self.ui.dorksCategoryList.addItem(category)

    def load_dorks_by_category(self, item):
        category = item.text()
        self.ui.dorksList.clear()
        dorks = self.google_dorks_db.get_dorks_by_category(category)
        for dork in dorks:
            self.ui.dorksList.addItem(dork)

    def search_dork(self, item):
        use_custom_dork = self.ui.useCustomDorkCheck.isChecked()
        use_searxng = self.ui.useSearxngCheck.isChecked()

        if not use_custom_dork:
            dork = item.text() if hasattr(item, "text") else item
            invoke(
                self.ui.dorksResult,
                "setPlainText",
                self.dorks_search_engine.search_dork(dork, use_searxng),
            )
        else:
            dork = self.ui.customDorkEdit.text()
            invoke(
                self.ui.dorksResult,
                "setPlainText",
                self.dorks_search_engine.search_dork(dork, use_searxng),
            )
