import asyncio
from typing import TYPE_CHECKING

from src.utils import filter_list, find_text

if TYPE_CHECKING:
    from src.controllers.domain_controller import DomainController
    from src.controllers.dorking_controller import DorkingController
    from src.controllers.intelx_controller import IntelxController
    from src.controllers.file_analyzer_controller import FileAnalyzeController
    from src.controllers.settings_controller import Settings


def setup_dorking_connectors(controller: "DorkingController"):
    controller.ui.dorksCategoryList.itemDoubleClicked.connect(
        lambda item: asyncio.ensure_future(controller.load_dorks_by_category(item))
    )
    controller.ui.dorksList.itemDoubleClicked.connect(
        lambda item: asyncio.ensure_future(controller.search_dork(item))
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
            controller.ui.metadataStatusLabel.setText(controller.get_file_type(path)),
            controller.start_file_analyzer(controller.ui.metadataFileDropWidget.get_file_path())
        )
    )

    controller.ui.getMetadataButton.clicked.connect(
        lambda: (
            asyncio.ensure_future(
                controller.start_file_analyzer(controller.ui.metadataFileDropWidget.get_file_path())
            ),
        )
    )
