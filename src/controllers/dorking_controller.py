from typing import TYPE_CHECKING

from loguru import logger

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

    async def load_categories(self):
        categories = self.google_dorks_db.getAllCategories()
        for category in categories:
            self.ui.dorksCategoryList.addItem(category)

    async def load_dorks_by_category(self, item):
        category = item.text()
        self.ui.dorksList.clear()
        dorks = self.google_dorks_db.getDorksByCategory(category)
        for dork in dorks:
            self.ui.dorksList.addItem(dork)

    async def search_dork(self, item):
        dork = item.text()
        useSearxng = self.ui.useSearxngCheck.isChecked()
        self.ui.dorksResult.setPlainText(self.dorks_search_engine.search_dork(dork, useSearxng))
