from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow
    from modules.google_dorks import GoogleDorksDB
    from modules.dorks_search_engine import DorksSearchEngine


class DorkingController:
    def __init__(
        self,
        ui: "QMainWindow",
        google_dorks_db: "GoogleDorksDB",
        dorks_search_engine: "DorksSearchEngine",
    ):
        self.ui = ui
        self.google_dorks_db = google_dorks_db
        self.dorks_search_engine = dorks_search_engine

    def load_categories(self):
        categories = self.google_dorks_db.getAllCategories()
        for category in categories:
            self.ui.dorksCategoryList.addItem(category)

    def load_dorks_by_category(self, item):
        category = item.text()
        self.ui.dorksList.clear()
        dorks = self.google_dorks_db.getDorksByCategory(category)
        for dork in dorks:
            self.ui.dorksList.addItem(dork)

    def search_dork(self, item):
        dork = item.text()
        self.ui.dorksResult.setPlainText(
            self.dorks_search_engine.search_dork(dork)
        )
