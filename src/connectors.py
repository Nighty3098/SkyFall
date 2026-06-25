import asyncio
from typing import TYPE_CHECKING

from src.context_menus import open_dorks_list_menu
from src.controllers.username_search_controller import UsernameController
from src.modules.metadata_cleaner import remove_metadata
from src.utils import filter_list, find_text

if TYPE_CHECKING:
    from src.controllers.domain_controller import DomainController
    from src.controllers.dorking_controller import DorkingController
    from src.controllers.file_analyzer_controller import FileAnalyzeController
    from src.controllers.github_controller import GitHubController
    from src.controllers.intelx_controller import IntelxController
    from src.controllers.mac_location_controller import MacLocationController
    from src.controllers.phone_controller import PhoneController
    from src.controllers.proxy_controller import Proxy
    from src.controllers.settings_controller import Settings
    from src.controllers.tg_analyzer_controller import TgAnalyzerController
    from src.controllers.tg_downloader_controller import TgDownloaderController


def setup_dorking_connectors(controller: "DorkingController"):
    controller.ui.dorksCategoryList.itemDoubleClicked.connect(
        lambda item: asyncio.ensure_future(controller.load_dorks_by_category(item))
    )
    controller.ui.dorksList.itemDoubleClicked.connect(
        lambda item: asyncio.ensure_future(controller.search_dork(item))
    )

    controller.ui.dorksList.customContextMenuRequested.connect(
        lambda pos: open_dorks_list_menu(
            controller.ui.dorksList, controller.ui.customDorkEdit, pos
        )
    )

    controller.ui.dorksCategorySearchEdit.textChanged.connect(
        lambda text: filter_list(controller.ui.dorksCategoryList, text)
    )
    controller.ui.dorksListSearchEdit.textChanged.connect(
        lambda text: filter_list(controller.ui.dorksList, text)
    )

    controller.ui.dorksResultSearchEdit.textChanged.connect(
        lambda text: find_text(controller, text)
    )

    controller.ui.dorkItButton.clicked.connect(
        lambda: asyncio.ensure_future(controller.search_dork(0))
    )


def setup_settings_connectors(settings: "Settings"):
    settings.ui.pushButton.clicked.connect(settings.save)


def setup_proxies_connectors(proxy: "Proxy"):
    proxy.ui.saveProxiesButton.clicked.connect(proxy.save_proxies)


def setup_domain_connectors(controller: "DomainController"):
    controller.ui.runUrlScanButton.clicked.connect(
        lambda: (
            controller.set_domain(controller.ui.serverUrlEdit.text()),
            asyncio.ensure_future(controller.analyze_domain()),
        )
    )


def setup_intelx_connectors(controller: "IntelxController"):
    controller.ui.startMailSearchButton.clicked.connect(
        lambda: (
            asyncio.ensure_future(
                controller.start_searching(controller.ui.mailEdit.text())
            ),
        )
    )


def setup_metadata_connectors(controller: "FileAnalyzeController"):
    controller.ui.metadataFileDropWidget.file_dropped.connect(
        lambda path: (
            controller.ui.metadataFilePath.setText(f"File: {path}"),
            asyncio.ensure_future(
                controller.start_file_analyzer(
                    controller.ui.metadataFileDropWidget.get_file_path()
                )
            ),
        )
    )

    controller.ui.getMetadataButton.clicked.connect(
        lambda: (
            asyncio.ensure_future(
                controller.start_file_analyzer(
                    controller.ui.metadataFileDropWidget.get_file_path()
                )
            ),
        )
    )

    controller.ui.cleanMetadataButton.clicked.connect(
        lambda: (
            remove_metadata(controller.ui.metadataFileDropWidget.get_file_path()),
            asyncio.ensure_future(
                controller.start_file_analyzer(
                    controller.ui.metadataFileDropWidget.get_file_path()
                )
            ),
        )
    )


def setup_username_connectors(controller: "UsernameController"):
    controller.ui.searchUsernameButton.clicked.connect(
        lambda: asyncio.ensure_future(
            controller.start_searching(controller.ui.usernameEdit.text())
        )
    )


def setup_tg_downloader_connectors(controller: "TgDownloaderController"):
    controller.ui.telegramDownloadStart.clicked.connect(
        lambda: asyncio.ensure_future(
            controller.start_collection(controller.build_collection_config())
        )
    )
    controller.ui.telegramDownloadAvatarsBtn.clicked.connect(
        lambda: asyncio.ensure_future(controller.start_avatar_download())
    )


def setup_tg_analyzer_connectors(controller: "TgAnalyzerController"):
    from datetime import datetime, timedelta

    from PySide6.QtCore import QDateTime

    controller.ui.telegramAnalyzerStartDate.setDateTime(
        QDateTime(datetime.now() - timedelta(days=365))
    )
    controller.ui.telegramAnalyzerEndDate.setDateTime(QDateTime(datetime.now()))
    controller.ui.telegramAnalyzerMinReplies.setValue(1)

    controller.ui.telegramAnalyzerLoadChannelsButton.clicked.connect(
        lambda: controller.load_channels(controller.ui.pathToStorageEdit.text())
    )
    controller.ui.runTelegramAnalyzerBtn.clicked.connect(
        lambda: asyncio.ensure_future(
            controller.run_analysis(controller.build_analysis_params())
        )
    )


def setup_github_connectors(controller: "GitHubController"):
    controller.ui.githubUserSearchBtn.clicked.connect(
        lambda: asyncio.ensure_future(controller.search_user())
    )
    controller.ui.githubRepoSearchBtn.clicked.connect(
        lambda: asyncio.ensure_future(controller.search_repos())
    )
    controller.ui.githubEmailSearchBtn.clicked.connect(
        lambda: asyncio.ensure_future(controller.search_emails())
    )
    controller.ui.githubCommitSearchBtn.clicked.connect(
        lambda: asyncio.ensure_future(controller.search_commits())
    )
    controller.ui.githubSecretSearchBtn.clicked.connect(
        lambda: asyncio.ensure_future(controller.search_secrets())
    )
    controller.ui.githubDorkSearchBtn.clicked.connect(
        lambda: asyncio.ensure_future(controller.search_dork())
    )


def setup_phone_connectors(controller: "PhoneController"):
    controller.ui.phoneParseBtn.clicked.connect(
        lambda: asyncio.ensure_future(controller.parse_validate())
    )
    controller.ui.phoneLookupBtn.clicked.connect(
        lambda: asyncio.ensure_future(controller.reverse_lookup())
    )
    controller.ui.phoneLeakBtn.clicked.connect(
        lambda: asyncio.ensure_future(controller.check_leaks())
    )


def setup_mac_location_connectors(controller: "MacLocationController"):
    controller.ui.checkMacAddrButton.clicked.connect(
        lambda: asyncio.ensure_future(controller.start_searching())
    )
