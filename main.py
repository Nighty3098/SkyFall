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
    setup_metadata_connectors,
    setup_settings_connectors,
)
from src.controllers.domain_controller import DomainController
from src.controllers.dorking_controller import DorkingController
from src.controllers.intelx_controller import IntelxController
from src.controllers.file_analyzer_controller import FileAnalyzeController
from src.controllers.settings_controller import Settings
from src.modules.domain_analyzer import DomainAnalyzer
from src.modules.dorks_search_engine import DorksSearchEngine
from src.modules.google_dorks import GoogleDorksDB
from src.modules.intelx_search_engine import IntelxSearchEngine
from src.modules.file_analyzer import FileAnalyzer
from src.shortcuts import ShortcutManager
from src.ui.drop_widget import DropWidget
from src.ui.setup_ui import setup_ui


class Loader(QUiLoader):
    def createWidget(self, class_name, parent=None, name=""):
        if class_name == "DropWidget":
            widget = DropWidget(parent)
            widget.setObjectName(name)
            return widget
        return super().createWidget(class_name, parent, name)

setup_logging()


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        ui_file = Path(__file__).parent / "resources" / "form.ui"
        self.ui = Loader().load(ui_file)
        self.setCentralWidget(self.ui)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        self._init_modules()
        setup_ui(self)
        self._shortcuts_manager = ShortcutManager(self)

    def _init_modules(self):
        logger.debug("Init modules")
        self.settings = Settings(self.ui)
        self.dorksSearchEngine = DorksSearchEngine()
        self.googleDorksDB = GoogleDorksDB()
        self.domainAnalyzer = DomainAnalyzer()
        self.fileAnalyzer = FileAnalyzer()
        self.intelxSearchEngine = IntelxSearchEngine(
            self.settings.intelligent_x_api_key
        )

    async def _async_init(self):
        logger.debug("Init controllers")

        self.dorkingController = DorkingController(
            self.ui, self.googleDorksDB, self.dorksSearchEngine
        )
        await self.dorkingController.load_categories()

        self.domainController = DomainController(self.ui, self.domainAnalyzer)
        self.fileAnalyzeController = FileAnalyzeController(self.ui, self.fileAnalyzer)
        self.IntelxController = IntelxController(self.ui, self.intelxSearchEngine)

        setup_dorking_connectors(self.dorkingController)
        setup_domain_connectors(self.domainController)
        setup_settings_connectors(self.settings)
        setup_metadata_connectors(self.fileAnalyzeController)
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
