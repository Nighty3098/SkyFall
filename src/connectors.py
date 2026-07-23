import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog

from src.context_menus import open_dorks_list_menu
from src.controllers.username_search_controller import UsernameController
from src.libs.graph_lib import ENTITY_NAMES, NodeItem
from src.modules.metadata_cleaner import remove_metadata
from src.utils import filter_list, find_text

if TYPE_CHECKING:
    from src.controllers.blockchain_controller import BlockchainController
    from src.controllers.domain_controller import DomainController
    from src.controllers.dorking_controller import DorkingController
    from src.controllers.file_analyzer_controller import FileAnalyzeController
    from src.controllers.github_controller import GitHubController
    from src.controllers.mac_location_controller import MacLocationController
    from src.controllers.mail_controller import MailController
    from src.controllers.phone_controller import PhoneController
    from src.controllers.proxy_controller import Proxy
    from src.controllers.search4faces_controller import S4FController
    from src.controllers.settings_controller import Settings
    from src.controllers.steganography_controller import SteganographyController
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


def setup_mail_connectors(controller: "MailController"):
    controller.ui.startMailSearchButton.clicked.connect(
        lambda: (
            asyncio.ensure_future(
                controller.start_intelx_search(controller.ui.mailEdit.text())
            ),
        )
    )
    controller.ui.startHibpCheckButton.clicked.connect(
        lambda: (
            asyncio.ensure_future(
                controller.start_hibp_check(controller.ui.mailEdit.text())
            ),
        )
    )


def setup_metadata_connectors(controller: "FileAnalyzeController"):
    controller.ui.metadataFileDropWidget.file_dropped.connect(
        lambda path: (
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


def setup_steganography_connectors(controller: "SteganographyController"):
    controller.ui.steganoFileDrop.file_dropped.connect(
        lambda path: asyncio.ensure_future(
            controller.start_steganography_analysis(
                controller.ui.steganoFileDrop.get_file_path()
            )
        )
    )


def setup_s4f_connectors(controller: "S4FController"):
    controller.ui.s4fFileDropWidget.file_dropped.connect(
        lambda path: controller.on_image_dropped(
            controller.ui.s4fFileDropWidget.get_file_path()
        )
    )
    controller.ui.runS4FButton.clicked.connect(
        lambda: asyncio.ensure_future(controller.run_search())
    )
    controller.ui.s4fSearchEdit.returnPressed.connect(controller.search_next)


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
    controller.ui.phone7telBtn.clicked.connect(
        lambda: asyncio.ensure_future(controller.search_7tel())
    )


def setup_mac_location_connectors(controller: "MacLocationController"):
    controller.ui.checkMacAddrButton.clicked.connect(
        lambda: asyncio.ensure_future(controller.start_searching())
    )


def setup_blockchain_connectors(controller: "BlockchainController"):
    controller.ui.bcSearchButton.clicked.connect(
        lambda: asyncio.ensure_future(controller.search())
    )


def setup_graph_connectors(ui, node_controller, case_manager=None):
    data_dir = str(Path.home() / ".skyfall" / "data")
    if case_manager:
        data_dir = case_manager.get_graph_dir()

    def export_graph():
        path, _ = QFileDialog.getSaveFileName(
            ui, "Export Graph", data_dir, "JSON (*.json)"
        )
        if path:
            ui.graphWidget.save_to_json(path)

    def import_graph():
        path, _ = QFileDialog.getOpenFileName(
            ui, "Import Graph", data_dir, "JSON (*.json)"
        )
        if path:
            ui.graphWidget.load_from_json(path)

    def clear_graph():
        ui.graphWidget._scene.clear()

    def on_search_text_changed(text):
        ui.graphWidget.set_filter(text)

    def on_filter_combo_changed(text):
        if text == "All Types":
            for item in ui.graphWidget._scene.items():
                if isinstance(item, NodeItem):
                    item.setVisible(True)
            ui.graphWidget._scene.update()
            ui.graphSearchEdit.setText("")
            return
        for item in ui.graphWidget._scene.items():
            if isinstance(item, NodeItem):
                match = item.entity_type == text
                item.setVisible(match)
        ui.graphWidget._scene.update()

    def on_clear_filter():
        ui.graphSearchEdit.setText("")
        ui.graphFilterCombo.setCurrentIndex(0)

    ui.exportGraphButton.clicked.connect(export_graph)
    ui.importGraphButton.clicked.connect(import_graph)
    ui.graphClearButton.clicked.connect(clear_graph)
    ui.graphSearchEdit.textChanged.connect(on_search_text_changed)
    ui.graphClearFilterButton.clicked.connect(on_clear_filter)
    ui.graphFilterCombo.currentTextChanged.connect(on_filter_combo_changed)

    ui.graphFilterCombo.addItem("All Types")
    for etype in ENTITY_NAMES:
        ui.graphFilterCombo.addItem(etype)

    ui.entitySearchEdit.textChanged.connect(ui.entityPalette.set_filter)

    ui.nodeTypeCombo.addItems(ENTITY_NAMES)
    ui.nodeEvidenceList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    ui.nodeEvidenceList.itemDoubleClicked.connect(node_controller._open_evidence)
    ui.nodeEvidenceList.customContextMenuRequested.connect(
        node_controller._evidence_context_menu
    )
    ui.nodeTitleEdit.textChanged.connect(node_controller._on_title_changed)
    ui.nodeTypeCombo.currentTextChanged.connect(node_controller._on_type_changed)
    ui.nodeContentEdit.textChanged.connect(node_controller._on_content_changed)
    ui.nodeEvidenceAddFileBtn.clicked.connect(node_controller._add_file)
    ui.nodeEvidenceAddUrlBtn.clicked.connect(node_controller._add_url)
    ui.nodeEvidenceRemoveBtn.clicked.connect(node_controller._remove_evidence)
    ui.graphWidget.selectionChanged.connect(node_controller.show_node)


def setup_graph_transform_connectors(ui, controller):
    ui.graphWidget._transform_controller = controller


def setup_graph_layout_connectors(controller):
    from src.modules.graph_layout import LAYOUT_ALGORITHMS

    controller.ui.graphLayoutCombo.addItems(LAYOUT_ALGORITHMS.values())
    controller.ui.graphAutoLayoutButton.clicked.connect(
        lambda: controller.apply_layout(
            _reverse_layout_map(controller.ui.graphLayoutCombo.currentText())
        )
    )


def _reverse_layout_map(label: str) -> str:
    from src.modules.graph_layout import LAYOUT_ALGORITHMS

    for key, val in LAYOUT_ALGORITHMS.items():
        if val == label:
            return key
    return "spring"


def setup_mcp_connectors(controller):
    controller.ui.mcpToggleButton.clicked.connect(controller.toggle)


def setup_report_connectors(controller):
    controller.ui.generateReportButton.clicked.connect(
        lambda: asyncio.ensure_future(controller.generate_report())
    )
    controller.ui.saveReportButton.clicked.connect(controller.save_report)

    controller.ui.updateOllamaListButton.clicked.connect(
        lambda: asyncio.ensure_future(controller.update_ollama_models())
    )
