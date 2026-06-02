from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.metadata_analyzer import MetadataAnalyzer


class MetadataController:
    def __init__(
        self,
        ui: "QMainWindow",
        metadata_analyzer: "MetadataAnalyzer",
    ):
        logger.debug("Init: MetadataController")

        self.ui = ui
        self.metadata_analyzer = metadata_analyzer

    def start_metadata_analyzer(self, path):
        result = self.metadata_analyzer.get_metadata(path)
        self.ui.metadataDebug.setPlainText(result)

    def get_file_type(self, path):
        return self.metadata_analyzer.get_file_type(path)