import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.controllers.domain_controller import DomainController
    from src.controllers.dorking_controller import DorkingController


def setup_dorking_connectors(controller: "DorkingController"):
    controller.ui.dorksCategoryList.itemDoubleClicked.connect(
        controller.load_dorks_by_category
    )
    controller.ui.dorksList.itemDoubleClicked.connect(controller.search_dork)


def setup_domain_connectors(controller: "DomainController"):
    controller.ui.runUrlScanButton.clicked.connect(
        lambda: (
            controller.set_domain(controller.ui.serverUrlEdit.text()),
            asyncio.run(controller.analyze_domain()),
        )
    )
