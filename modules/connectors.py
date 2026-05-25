from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from modules.dorking_controller import DorkingController


def setup_dorking_connectors(controller: "DorkingController"):
    controller.ui.dorksCategoryList.itemDoubleClicked.connect(
        controller.load_dorks_by_category
    )
    controller.ui.dorksList.itemDoubleClicked.connect(
        controller.search_dork
    )
