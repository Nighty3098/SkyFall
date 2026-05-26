import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from modules.domain_controller import DomainController

def setup_domain_connectors(controller: "DomainController"):
    controller.ui.runUrlScanButton.clicked.connect(
        lambda: (
            controller.set_domain(controller.ui.serverUrlEdit.text()),
            asyncio.run(controller.analyze_domain()),
        )
    )
