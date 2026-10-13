import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "thirdparty" / "txfetch"))

from loguru import logger
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QMainWindow
from qasync import QEventLoop

from logger_setup import setup_logging
from src.case_manager import CaseManager
from src.connectors import (
    setup_archive_connectors,
    setup_blockchain_connectors,
    setup_domain_connectors,
    setup_dorking_connectors,
    setup_download_connectors,
    setup_geo_connectors,
    setup_github_connectors,
    setup_graph_connectors,
    setup_graph_layout_connectors,
    setup_graph_transform_connectors,
    setup_leak_connectors,
    setup_mac_location_connectors,
    setup_mail_connectors,
    setup_mcp_connectors,
    setup_metadata_connectors,
    setup_phone_connectors,
    setup_proxies_connectors,
    setup_reddit_connectors,
    setup_report_connectors,
    setup_s4f_connectors,
    setup_settings_connectors,
    setup_social_connectors,
    setup_steganography_connectors,
    setup_tg_analyzer_connectors,
    setup_tg_downloader_connectors,
    setup_username_connectors,
)
from src.controllers.archive_controller import ArchiveController
from src.controllers.blockchain_controller import BlockchainController
from src.controllers.domain_controller import DomainController
from src.controllers.dorking_controller import DorkingController
from src.controllers.download_controller import DownloadController
from src.controllers.file_analyzer_controller import FileAnalyzeController
from src.controllers.geo_controller import GeoController
from src.controllers.github_controller import GitHubController
from src.controllers.graph_layout_controller import GraphLayoutController
from src.controllers.graph_node_controller import GraphNodeController
from src.controllers.graph_transform_controller import GraphTransformController
from src.controllers.leak_controller import LeakController
from src.controllers.mac_location_controller import MacLocationController
from src.controllers.mail_controller import MailController
from src.controllers.phone_controller import PhoneController
from src.controllers.proxy_controller import Proxy
from src.controllers.reddit_osint_controller import RedditOsintController
from src.controllers.search4faces_controller import S4FController
from src.controllers.settings_controller import Settings
from src.controllers.social_controller import SocialController
from src.controllers.steganography_controller import SteganographyController
from src.controllers.tg_analyzer_controller import TgAnalyzerController
from src.controllers.tg_downloader_controller import TgDownloaderController
from src.controllers.username_search_controller import UsernameController
from src.libs.graph_lib import GraphWidget, NodeItem
from src.libs.graph_panel import EntityPalette
from src.mcp_controller import McpController
from src.modules.archive_search import ArchiveSearch
from src.modules.blockchain_search import BlockchainSearch
from src.modules.domain_analyzer import DomainAnalyzer
from src.modules.dorks_search_engine import DorksSearchEngine
from src.modules.downloader import DownloadManager
from src.modules.email_accounts import EmailAccounts
from src.modules.email_header_analyzer import EmailHeaderAnalyzer
from src.modules.file_analyzer import FileAnalyzer
from src.modules.geo_analysis import GeoAnalysis
from src.modules.github_search import GitHubSearch
from src.modules.google_dorks import GoogleDorksDB
from src.modules.leak_search import LeakSearch
from src.modules.mac_location import MacLocation
from src.modules.maigret_search import MaigretSearch
from src.modules.mail_search_engine import MailSearchEngine
from src.modules.phone_search import PhoneSearch
from src.modules.reddit_osint import RedditOsint
from src.modules.search4faces import Search4Faces
from src.modules.social_search import SocialSearch
from src.modules.steganography import SteganographyAnalyzer
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
│                       SkyFall Ver 1.0.1                         │
│                      Coded by Nighty3098                        │
│                 https://nighty3098.vercel.app                   │
└─────────────────────────────────────────────────────────────────┘
            """)
        super().__init__(parent)

        ui_file = Path(__file__).parent / "resources" / "form.ui"
        self.ui = Loader().load(ui_file)
        self.setCentralWidget(self.ui)

        self.settings = Settings(self.ui)
        if self.settings.frameless_window:
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        self.case_manager = CaseManager(self.ui.menu_SkyFall)
        self._init_modules()
        self.settings.on_save(self._sync_tokens)
        setup_ui(self)
        self.ui.actionNew_case.triggered.connect(self.case_manager.create_case)
        self.ui.actionOpen_case.triggered.connect(self.case_manager.open_case)
        self.ui.actionExit.triggered.connect(self.close)
        self.ui.actionAbout.triggered.connect(self._show_about)
        self.ui.actionOpenGitHub.triggered.connect(self._open_github)
        self._shortcuts_manager = ShortcutManager(
            self, self.ui.mainStackedWidget, self.ui.menuListWidget
        )

        self.init_font("resources/Caveat-VariableFont_wght.ttf")
        self.init_font("resources/IosevkaCharonMono-Regular.ttf")
        self.init_font("resources/BebasNeue-Regular.ttf")

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
        if hasattr(self, "mcpController"):
            self.mcpController.cleanup()
        if hasattr(self, "fileAnalyzer"):
            self._close_task = asyncio.ensure_future(self.fileAnalyzer.close())
        super().closeEvent(event)

    def eventFilter(self, obj, event):
        if obj is getattr(self.ui, "sourceCodeLinkLabel", None) and event.type() in (
            QEvent.Type.MouseButtonRelease,
            QEvent.Type.MouseButtonDblClick,
        ):
            self._open_github()
            return True
        return super().eventFilter(obj, event)

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
        self.downloadManager = DownloadManager()
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
            getattr(self.settings, "abuseipdb_api_key", ""),
            getattr(self.settings, "greynoise_api_key", ""),
        )
        self.tgAnalyzer = TgAnalyzer()
        self.tgDownloader = TgDownloader(
            {
                "api_id": self.ui.tgApiKeyEdit.text(),
                "api_hash": self.ui.telegramApiHashEdit.text(),
                "channel": "",
                "path": tg_data_path,
                "proxy_list": self.proxy.get_proxy_url() or "",
            }
        )
        self.fileAnalyzer = FileAnalyzer(self.settings.virustotal_api_key)
        self.stegAnalyzer = SteganographyAnalyzer()
        self.search4faces = Search4Faces()
        self.mailSearchEngine = MailSearchEngine(
            self.settings.intelligent_x_api_key,
            self.settings.hibp_api_key,
        )
        self.emailHeaderAnalyzer = EmailHeaderAnalyzer()
        self.emailAccounts = EmailAccounts()
        self.socialSearch = SocialSearch()
        self.redditOsint = RedditOsint(
            client_id=getattr(self.settings, "reddit_client_id", ""),
            client_secret=getattr(self.settings, "reddit_client_secret", ""),
        )
        self.leakSearch = LeakSearch()
        self.geoAnalysis = GeoAnalysis()
        self.archiveSearch = ArchiveSearch()
        self.blockchainSearch = BlockchainSearch(
            {
                "trongrid_api_key": self.settings.trongrid_api_key,
                "etherscan_api_key": self.settings.etherscan_api_key,
                "bscscan_api_key": self.settings.bscscan_api_key,
                "tonapi_api_key": self.settings.tonapi_api_key,
                "helius_api_key": self.settings.helius_api_key,
            }
        )

        self._sync_tokens(self.settings)

    def _sync_tokens(self, settings):
        self.githubSearch._token = settings.github_token
        self.githubSearch._headers["Authorization"] = f"Bearer {settings.github_token}"

        self.domainAnalyzer.API_KEYS["VIRUSTOTAL"] = settings.virustotal_api_key
        self.domainAnalyzer.API_KEYS["GOOGLE_SAFE"] = settings.google_safe_api_key
        self.domainAnalyzer.API_KEYS["IPINFO"] = settings.ipinfo_api_key
        self.domainAnalyzer.update_threat_keys(
            getattr(settings, "abuseipdb_api_key", ""),
            getattr(settings, "greynoise_api_key", ""),
        )

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

        if hasattr(self, "leakSearch"):
            self.leakSearch.keys = {
                "leakcheck_api_key": getattr(settings, "leakcheck_api_key", ""),
                "dehashed_email": getattr(settings, "dehashed_email", ""),
                "dehashed_api_key": getattr(settings, "dehashed_api_key", ""),
                "hibp_api_key": settings.hibp_api_key,
            }
            if hasattr(self, "leakController"):
                self.leakController.keys = self.leakSearch.keys
        if hasattr(self, "geoAnalysis"):
            self.geoAnalysis.firms_key = getattr(settings, "firms_map_key", "")
            if hasattr(self, "geoController"):
                self.geoController.firms_key = self.geoAnalysis.firms_key

        if hasattr(self, "redditOsint"):
            self.redditOsint.set_credentials(
                getattr(settings, "reddit_client_id", ""),
                getattr(settings, "reddit_client_secret", ""),
            )

    def _show_about(self):
        from PySide6.QtGui import QPixmap
        from PySide6.QtWidgets import QDialog, QLabel, QSpacerItem, QVBoxLayout

        dlg = QDialog(self)
        dlg.setWindowTitle("About SkyFall")
        dlg.setFixedSize(400, 500)

        layout = QVBoxLayout(dlg)
        layout.setAlignment(Qt.AlignCenter)

        icon_path = Path(__file__).parent / "resources" / "icon.png"
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            icon = QLabel()
            icon.setPixmap(
                pixmap.scaled(256, 256, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            icon.setAlignment(Qt.AlignCenter)
            layout.addWidget(icon)

        layout.addSpacerItem(QSpacerItem(0, 50))

        text = QLabel(
            "<h1>SkyFall 1.0.1</h1>"
            "<p>OSINT investigation toolkit</p>"
            "<p>Coded by <a href='https://nighty3098.vercel.app'>Nighty3098</a></p>"
        )
        text.setAlignment(Qt.AlignCenter)
        text.setOpenExternalLinks(True)
        layout.addWidget(text)

        dlg.exec()

    def _open_github(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl("https://github.com/Nighty3098/SkyFall"))

    async def _async_init(self):
        logger.debug("Init controllers")

        self.dorkingController = DorkingController(
            self.ui, self.googleDorksDB, self.dorksSearchEngine
        )
        await self.dorkingController.load_categories()

        self.downloadController = DownloadController(
            self.ui,
            self.downloadManager,
            settings=self.settings,
            case_manager=self.case_manager,
            proxy=self.proxy,
        )
        setup_download_connectors(self.downloadController)

        self.domainController = DomainController(self.ui, self.domainAnalyzer)
        self.fileAnalyzeController = FileAnalyzeController(self.ui, self.fileAnalyzer)
        self.stegController = SteganographyController(self.ui, self.stegAnalyzer)
        self.mailController = MailController(
            self.ui,
            self.mailSearchEngine,
            header_analyzer=self.emailHeaderAnalyzer,
            email_accounts=self.emailAccounts,
        )
        self.usernameController = UsernameController(
            self.ui, self.usernameSearch, self.maigretSearch, proxy=self.proxy
        )
        self.socialController = SocialController(self.ui, self.socialSearch)
        self.redditController = RedditOsintController(
            self.ui,
            self.redditOsint,
            proxy=self.proxy,
            case_manager=self.case_manager,
        )
        self.leakController = LeakController(
            self.ui,
            self.leakSearch,
            keys={
                "leakcheck_api_key": getattr(self.settings, "leakcheck_api_key", ""),
                "dehashed_email": getattr(self.settings, "dehashed_email", ""),
                "dehashed_api_key": getattr(self.settings, "dehashed_api_key", ""),
                "hibp_api_key": self.settings.hibp_api_key,
            },
        )
        self.geoController = GeoController(
            self.ui,
            self.geoAnalysis,
            firms_key=getattr(self.settings, "firms_map_key", ""),
        )
        self.archiveController = ArchiveController(self.ui, self.archiveSearch)
        self.macLocationController = MacLocationController(self.ui, self.macLocation)
        self.tgDownloaderController = TgDownloaderController(
            self.ui,
            self.tgDownloader,
            self.proxy,
            self.case_manager,
            file_analyzer=self.fileAnalyzer,
        )
        self.tgAnalyzerController = TgAnalyzerController(
            self.ui, self.tgAnalyzer, graph_widget=self.ui.graphWidget
        )
        self.githubController = GitHubController(self.ui, self.githubSearch)
        self.phoneController = PhoneController(
            self.ui,
            self.phoneSearch,
            numverify_key=self.settings.numverify_api_key,
            abstractapi_key=self.settings.abstractapi_api_key,
            intelx_key=self.settings.intelligent_x_api_key,
        )

        self.blockchainController = BlockchainController(self.ui, self.blockchainSearch)
        self.nodeController = GraphNodeController(self.ui)
        self.s4fController = S4FController(self.ui, self.search4faces)

        setup_dorking_connectors(self.dorkingController)
        setup_domain_connectors(self.domainController)
        setup_settings_connectors(self.settings)
        setup_metadata_connectors(self.fileAnalyzeController)
        setup_steganography_connectors(self.stegController)
        setup_mail_connectors(self.mailController)
        setup_username_connectors(self.usernameController)
        setup_social_connectors(self.socialController)
        setup_reddit_connectors(self.redditController)
        setup_leak_connectors(self.leakController)
        setup_geo_connectors(self.geoController)
        setup_archive_connectors(self.archiveController)
        setup_tg_downloader_connectors(self.tgDownloaderController)
        setup_tg_analyzer_connectors(self.tgAnalyzerController)
        setup_proxies_connectors(self.proxy)
        setup_github_connectors(self.githubController)
        setup_phone_connectors(self.phoneController)
        setup_mac_location_connectors(self.macLocationController)
        setup_blockchain_connectors(self.blockchainController)
        setup_s4f_connectors(self.s4fController)

        self.graphTransformController = GraphTransformController(
            self.ui.graphWidget,
            {
                "domain_analyzer": self.domainAnalyzer,
                "username_search": self.usernameSearch,
                "maigret_search": self.maigretSearch,
                "reddit_osint": self.redditOsint,
                "phone_search": self.phoneSearch,
                "mac_location": self.macLocation,
                "mail_search": self.mailSearchEngine,
                "email_accounts": self.emailAccounts,
                "social_search": self.socialSearch,
                "leak_search": self.leakSearch,
                "geo_analysis": self.geoAnalysis,
                "archive_search": self.archiveSearch,
            },
        )
        self.reportController = ReportController(self.ui, self.case_manager)
        setup_report_connectors(self.reportController)
        setup_graph_transform_connectors(self.ui, self.graphTransformController)
        setup_graph_connectors(self.ui, self.nodeController, self.case_manager)

        self.graphLayoutController = GraphLayoutController(self.ui, self.ui.graphWidget)
        setup_graph_layout_connectors(self.graphLayoutController)

        self.mcpController = McpController(self.ui)
        self.mcpController.set_graph_bridge(self.ui.graphWidget, NodeItem)
        setup_mcp_connectors(self.mcpController)

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
    # Wayland app-id должен совпадать с именем skyfall.desktop,
    # иначе DE покажет generic-иконку вместо нашей.
    app.setApplicationName("skyfall")
    app.setOrganizationName("skyfall")
    app.setDesktopFileName("skyfall")
    widget = MainWindow()

    widget.show()

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    widget._async_init_task = asyncio.ensure_future(widget._async_init())
    loop.run_forever()
    loop.close()
