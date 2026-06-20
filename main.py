import argparse
import asyncio
import sys
from pathlib import Path

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QMainWindow
from qasync import QEventLoop

from logger_setup import setup_logging
from src.connectors import (
    setup_domain_connectors,
    setup_dorking_connectors,
    setup_intelx_connectors,
    setup_metadata_connectors,
    setup_proxies_connectors,
    setup_settings_connectors,
    setup_tg_analyzer_connectors,
    setup_tg_downloader_connectors,
    setup_username_connectors,
)
from src.controllers.domain_controller import DomainController
from src.controllers.dorking_controller import DorkingController
from src.controllers.file_analyzer_controller import FileAnalyzeController
from src.controllers.intelx_controller import IntelxController
from src.controllers.proxy_controller import Proxy
from src.controllers.settings_controller import Settings
from src.controllers.tg_analyzer_controller import TgAnalyzerController
from src.controllers.tg_downloader_controller import TgDownloaderController
from src.controllers.username_search_controller import UsernameController
from src.modules.domain_analyzer import DomainAnalyzer
from src.modules.dorks_search_engine import DorksSearchEngine
from src.modules.file_analyzer import FileAnalyzer
from src.modules.google_dorks import GoogleDorksDB
from src.modules.intelx_search_engine import IntelxSearchEngine
from src.modules.tg_analyzer import TgAnalyzer
from src.modules.tg_downloader import TgDownloader
from src.modules.username_search import UsernameSearch
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


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        print("""
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│            _______ __          _______       __ __              │
│           |   _   |  |--.--.--|   _   .---.-|  |  |             │
│           |   1___|    <|  |  |.  1___|  _  |  |  |             │
│           |____   |__|__|___  |.  __) |___._|__|__|             │
│           |:  1   |     |_____|:  |                             │
│           |::.. . |           |::.|                             │
│           `-------'           `---'                             │
│                                                                 │
│                      SkyFall Ver. 1.0                           │
│                    Coded by Nighty3098                          │
│               https://nighty3098.vercel.app                     │
└─────────────────────────────────────────────────────────────────┘
            """)
        super().__init__(parent)
        ui_file = Path(__file__).parent / "resources" / "form.ui"
        self.ui = Loader().load(ui_file)
        self.setCentralWidget(self.ui)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        self._init_modules()
        setup_ui(self)
        self._shortcuts_manager = ShortcutManager(
            self, self.ui.mainStackedWidget, self.ui.menuListWidget
        )
        self.init_font("resources/Caveat-VariableFont_wght.ttf")
        self.init_font("resources/IosevkaCharonMono-Regular.ttf")

    def init_font(self, font_path):
        font_id = QFontDatabase.addApplicationFont(font_path)

        if font_id == -1:
            logger.error(f"Error loading font: {font_path}")
            return None

        font_families = QFontDatabase.applicationFontFamilies(font_id)
        if font_families:
            logger.debug(f"Loaded font: {font_path}")
            return font_families[0]
        return None

    def closeEvent(self, event):
        if hasattr(self, "fileAnalyzer"):
            asyncio.ensure_future(self.fileAnalyzer.close())
        super().closeEvent(event)

    def _init_modules(self):
        logger.debug("Init modules")
        self.settings = Settings(self.ui)
        self.proxy = Proxy(self.ui)
        from pathlib import Path
        tg_data_path = str(Path.home() / ".skyfall" / "data")
        self.dorksSearchEngine = DorksSearchEngine()
        self.googleDorksDB = GoogleDorksDB()
        self.usernameSearch = UsernameSearch()
        self.domainAnalyzer = DomainAnalyzer(
            self.settings.virustotal_api_key,
            self.settings.google_safe_api_key,
            self.settings.ipinfo_api_key,
        )
        self.tgAnalyzer = TgAnalyzer()
        self.tgDownloader = TgDownloader(
            {
                "api_id": self.ui.tgApiKeyEdit.text(),
                "api_hash": self.ui.telegramApiHashEdit.text(),
                "channel": "",
                "path": tg_data_path,
                "proxy_list": self.proxy.get_proxies_text(),
            }
        )
        self.fileAnalyzer = FileAnalyzer(self.settings.virustotal_api_key)
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
        self.usernameController = UsernameController(self.ui, self.usernameSearch)
        self.tgDownloaderController = TgDownloaderController(
            self.ui, self.tgDownloader, self.proxy
        )
        self.tgAnalyzerController = TgAnalyzerController(self.ui, self.tgAnalyzer)

        setup_dorking_connectors(self.dorkingController)
        setup_domain_connectors(self.domainController)
        setup_settings_connectors(self.settings)
        setup_metadata_connectors(self.fileAnalyzeController)
        setup_intelx_connectors(self.IntelxController)
        setup_username_connectors(self.usernameController)
        setup_tg_downloader_connectors(self.tgDownloaderController)
        setup_tg_analyzer_connectors(self.tgAnalyzerController)
        setup_proxies_connectors(self.proxy)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", action="store_true")
    args = parser.parse_args()

    if args.debug:
        setup_logging(True)
    else:
        setup_logging(False)

    app = QApplication(sys.argv)
    widget = MainWindow()

    widget.show()

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    asyncio.ensure_future(widget._async_init())
    loop.run_forever()
    loop.close()
