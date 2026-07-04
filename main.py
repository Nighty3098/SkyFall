import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "thirdparty" / "txfetch"))

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QMainWindow
from qasync import QEventLoop

from logger_setup import setup_logging
from src.case_manager import CaseManager
from src.connectors import (
    setup_blockchain_connectors,
    setup_domain_connectors,
    setup_dorking_connectors,
    setup_github_connectors,
    setup_graph_connectors,
    setup_graph_transform_connectors,
    setup_mac_location_connectors,
    setup_mail_connectors,
    setup_metadata_connectors,
    setup_phone_connectors,
    setup_proxies_connectors,
    setup_report_connectors,
    setup_settings_connectors,
    setup_tg_analyzer_connectors,
    setup_tg_downloader_connectors,
    setup_username_connectors,
)
from src.controllers.blockchain_controller import BlockchainController
from src.controllers.domain_controller import DomainController
from src.controllers.dorking_controller import DorkingController
from src.controllers.file_analyzer_controller import FileAnalyzeController
from src.controllers.github_controller import GitHubController
from src.controllers.graph_transform_controller import (
    GraphTransformController,
)
from src.controllers.mac_location_controller import MacLocationController
from src.controllers.mail_controller import MailController
from src.controllers.phone_controller import PhoneController
from src.controllers.proxy_controller import Proxy
from src.controllers.settings_controller import Settings
from src.controllers.tg_analyzer_controller import TgAnalyzerController
from src.controllers.tg_downloader_controller import TgDownloaderController
from src.controllers.username_search_controller import UsernameController
from src.libs.graph_lib import GraphWidget
from src.libs.graph_panel import EntityPalette, PropertiesPanel
from src.modules.blockchain_search import BlockchainSearch
from src.modules.domain_analyzer import DomainAnalyzer
from src.modules.dorks_search_engine import DorksSearchEngine
from src.modules.file_analyzer import FileAnalyzer
from src.modules.github_search import GitHubSearch
from src.modules.google_dorks import GoogleDorksDB
from src.modules.mac_location import MacLocation
from src.modules.maigret_search import MaigretSearch
from src.modules.mail_search_engine import MailSearchEngine
from src.modules.phone_search import PhoneSearch
from src.modules.tg_analyzer import TgAnalyzer
from src.modules.tg_downloader import TgDownloader
from src.modules.username_search import UsernameSearch
from src.report_controller import ReportController
from src.shortcuts import ShortcutManager
from src.ui.drop_widget import DropWidget
from src.ui.setup_ui import setup_ui


class Loader(QUiLoader):
    def createWidget(self, class_name, parent=None, name=""):
        if class_name == "DropWidget":
            widget = DropWidget(parent)
            widget.setObjectName(name)
            return widget
        if class_name == "GraphWidget":
            widget = GraphWidget(parent)
            widget.setObjectName(name)
            return widget
        if class_name == "PropertiesPanel":
            widget = PropertiesPanel(parent)
            widget.setObjectName(name)
            return widget
        if class_name == "EntityPalette":
            widget = EntityPalette(parent)
            widget.setObjectName(name)
            return widget
        if class_name == "QWebEngineView":
            widget = QWebEngineView(parent)
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

        self.settings = Settings(self.ui)
        if self.settings.frameless_window:
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        self.case_manager = CaseManager()
        self._init_modules()
        self.settings.on_save(self._sync_tokens)
        setup_ui(self, self.case_manager)
        self._shortcuts_manager = ShortcutManager(
            self, self.ui.mainStackedWidget, self.ui.menuListWidget
        )

        self.ui.graphWidget.selectionChanged.connect(self.ui.nodeEditPanel.show_node)
        self.ui.nodeEditPanel._find_children()

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

    def _wire_case_auto_save(self):
        widget_names = list(self.case_manager.CATEGORY_MAP)
        for name in widget_names:
            widget = getattr(self.ui, name, None)
            if widget is None:
                continue
            widget.textChanged.connect(
                lambda n=name, w=widget: self.case_manager.save_result(
                    n, w.toPlainText()
                )
            )

    def _init_modules(self):
        logger.debug("Init modules")

        self.proxy = Proxy(self.ui)
        from pathlib import Path

        tg_data_path = str(Path.home() / ".skyfall" / "data")
        self.dorksSearchEngine = DorksSearchEngine()
        self.googleDorksDB = GoogleDorksDB()
        self.githubSearch = GitHubSearch(self.settings.github_token)
        self.phoneSearch = PhoneSearch()
        self.usernameSearch = UsernameSearch()
        self.macLocation = MacLocation()
        self.maigretSearch = MaigretSearch()
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
        self.mailSearchEngine = MailSearchEngine(
            self.settings.intelligent_x_api_key,
            self.settings.hibp_api_key,
        )
        self.blockchainSearch = BlockchainSearch(
            {
                "trongrid_api_key": self.settings.trongrid_api_key,
                "etherscan_api_key": self.settings.etherscan_api_key,
                "bscscan_api_key": self.settings.bscscan_api_key,
                "tonapi_api_key": self.settings.tonapi_api_key,
                "helius_api_key": self.settings.helius_api_key,
            }
        )

    def _sync_tokens(self, settings):
        self.githubSearch._token = settings.github_token
        self.githubSearch._headers["Authorization"] = f"Bearer {settings.github_token}"

        self.domainAnalyzer.API_KEYS["VIRUSTOTAL"] = settings.virustotal_api_key
        self.domainAnalyzer.API_KEYS["GOOGLE_SAFE"] = settings.google_safe_api_key
        self.domainAnalyzer.API_KEYS["IPINFO"] = settings.ipinfo_api_key

        self.mailSearchEngine.api_key = settings.intelligent_x_api_key
        self.mailSearchEngine.headers["x-key"] = settings.intelligent_x_api_key
        self.mailSearchEngine.hibp_api_key = settings.hibp_api_key

        self.fileAnalyzer.update_api_key(settings.virustotal_api_key)

        self.blockchainSearch._set_env_keys(
            {
                "trongrid_api_key": settings.trongrid_api_key,
                "etherscan_api_key": settings.etherscan_api_key,
                "bscscan_api_key": settings.bscscan_api_key,
                "tonapi_api_key": settings.tonapi_api_key,
                "helius_api_key": settings.helius_api_key,
            }
        )

        self.tgDownloader.api_id = settings.tg_api_key
        self.tgDownloader.api_hash = settings.telegram_api_hash

    async def _async_init(self):
        logger.debug("Init controllers")

        self.dorkingController = DorkingController(
            self.ui, self.googleDorksDB, self.dorksSearchEngine
        )
        await self.dorkingController.load_categories()

        self.domainController = DomainController(self.ui, self.domainAnalyzer)
        self.fileAnalyzeController = FileAnalyzeController(self.ui, self.fileAnalyzer)
        self.mailController = MailController(self.ui, self.mailSearchEngine)
        self.usernameController = UsernameController(
            self.ui, self.usernameSearch, self.maigretSearch
        )
        self.macLocationController = MacLocationController(self.ui, self.macLocation)
        self.tgDownloaderController = TgDownloaderController(
            self.ui, self.tgDownloader, self.proxy, self.case_manager
        )
        self.tgAnalyzerController = TgAnalyzerController(self.ui, self.tgAnalyzer)
        self.githubController = GitHubController(self.ui, self.githubSearch)
        self.phoneController = PhoneController(
            self.ui,
            self.phoneSearch,
            numverify_key=self.settings.numverify_api_key,
            abstractapi_key=self.settings.abstractapi_api_key,
            intelx_key=self.settings.intelligent_x_api_key,
        )

        self.blockchainController = BlockchainController(self.ui, self.blockchainSearch)

        setup_dorking_connectors(self.dorkingController)
        setup_domain_connectors(self.domainController)
        setup_settings_connectors(self.settings)
        setup_metadata_connectors(self.fileAnalyzeController)
        setup_mail_connectors(self.mailController)
        setup_username_connectors(self.usernameController)
        setup_tg_downloader_connectors(self.tgDownloaderController)
        setup_tg_analyzer_connectors(self.tgAnalyzerController)
        setup_proxies_connectors(self.proxy)
        setup_github_connectors(self.githubController)
        setup_phone_connectors(self.phoneController)
        setup_mac_location_connectors(self.macLocationController)
        setup_blockchain_connectors(self.blockchainController)

        self.graphTransformController = GraphTransformController(
            self.ui.graphWidget,
            {
                "domain_analyzer": self.domainAnalyzer,
                "username_search": self.usernameSearch,
                "maigret_search": self.maigretSearch,
                "phone_search": self.phoneSearch,
                "mac_location": self.macLocation,
                "mail_search": self.mailSearchEngine,
            },
        )
        self.reportController = ReportController(self.ui, self.case_manager)
        setup_report_connectors(self.reportController)
        setup_graph_transform_connectors(self.ui, self.graphTransformController)
        setup_graph_connectors(self.ui, self.case_manager)

        self._wire_case_auto_save()


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
