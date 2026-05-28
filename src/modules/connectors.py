import asyncio
from typing import TYPE_CHECKING

from src.utils import filter_list, find_text

if TYPE_CHECKING:
    from src.controllers.domain_controller import DomainController
    from src.controllers.dorking_controller import DorkingController


def setup_dorking_connectors(controller: "DorkingController"):
    controller.ui.dorksCategoryList.itemDoubleClicked.connect(
        lambda item: asyncio.run(controller.load_dorks_by_category(item))
    )
    controller.ui.dorksList.itemDoubleClicked.connect(
        lambda item: asyncio.run(controller.search_dork(item))
    )

    controller.ui.dorksCategorySearchEdit.textChanged.connect(
        lambda text: filter_list(controller.ui.dorksCategoryList, text)
    )
    controller.ui.dorksListSearchEdit.textChanged.connect(
        lambda text: filter_list(controller.ui.dorksList, text)
    )

    controller.ui.dorksResultSearchEdit.textChanged.connect(
        lambda text : find_text(controller, text)
    )


def setup_domain_connectors(controller: "DomainController"):
    controller.ui.runUrlScanButton.clicked.connect(
        lambda: (
            controller.set_domain(controller.ui.serverUrlEdit.text()),
            asyncio.run(controller.analyze_domain()),
        )
    )
