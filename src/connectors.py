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
    from src.controllers.intelx_controller import IntelxController
    from src.controllers.settings_controller import Settings


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
        lambda: (
            asyncio.ensure_future(
                controller.start_searching(controller.ui.usernameEdit.text())
            ),
        )
    )
