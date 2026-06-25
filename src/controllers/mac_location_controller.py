import asyncio
import json
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.mac_location import MacLocation


class MacLocationController:
    def __init__(
        self,
        ui: "QMainWindow",
        mac_location: "MacLocation",
    ):
        logger.debug("Init: MacLocationController")

        self.ui = ui
        self.mac_location = mac_location

    async def start_searching(self):
        result = await asyncio.to_thread(self.mac_location.locate, self.ui.macAddrEdit.text())
        lines = [f"MAC: {result['mac']}"]
        for provider, loc in result["location"].items():
            if loc is None:
                lines.append(f"  {provider}: no data")
            else:
                lines.append(f"  {provider}: {loc['latitude']}, {loc['longitude']}")
        self.ui.macAddrLocationDebug.setPlainText("\n".join(lines))
