import asyncio
import sys
from pathlib import Path

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QMainWindow
from qasync import QEventLoop

from logger_setup import setup_logging
from src.connectors import (
    setup_domain_connectors,
    setup_dorking_connectors,
    setup_intelx_connectors,
    setup_settings_connectors,
)
from src.controllers.domain_controller import DomainController
from src.controllers.dorking_controller import DorkingController
from src.controllers.intelx_controller import IntelxController
from src.controllers.settings_controller import Settings
from src.modules.domain_analyzer import DomainAnalyzer
from src.modules.dorks_search_engine import DorksSearchEngine
from src.modules.google_dorks import GoogleDorksDB
from src.modules.intelx_search_engine import IntelxSearchEngine
from src.shortcuts import ShortcutManager
from src.ui.setup_ui import setup_ui

setup_logging()


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        ui_file = Path(__file__).parent / "resources" / "form.ui"
        self.ui = QUiLoader().load(ui_file)
        self.setCentralWidget(self.ui)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        self._init_modules()
        setup_ui(self)
        self._shortcuts_manager = ShortcutManager(self)

    def _init_modules(self):
        logger.debug("Init modules")
        self.dorksSearchEngine = DorksSearchEngine()
        self.googleDorksDB = GoogleDorksDB()

    async def _async_init(self):
        logger.debug("Init controllers")

        self.settings = Settings(self.ui)

        self.dorkingController = DorkingController(
            self.ui, self.googleDorksDB, self.dorksSearchEngine
        )
        await self.dorkingController.load_categories()

        self.domainAnalyzer = DomainAnalyzer()
        self.domainController = DomainController(self.ui, self.domainAnalyzer)

        setup_dorking_connectors(self.dorkingController)
        setup_domain_connectors(self.domainController)
        setup_settings_connectors(self.settings)

        self.intelxSearchEngine = IntelxSearchEngine(
            self.settings.intelligent_x_api_key
        )

        self.IntelxController = IntelxController(self.ui, self.intelxSearchEngine)

        setup_intelx_connectors(self.IntelxController)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = MainWindow()

    try:
        with open("resources/style.qss", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        logger.warning("style.qss not found.")

    widget.show()

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    asyncio.ensure_future(widget._async_init())
    loop.run_forever()
    loop.close()
