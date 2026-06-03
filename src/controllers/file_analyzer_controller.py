from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.file_analyzer import FileAnalyzer


class FileAnalyzeController:
    def __init__(
        self,
        ui: "QMainWindow",
        file_analyzer: "FileAnalyzer",
    ):
        logger.debug("Init: FileAnalyzeController")

        self.ui = ui
        self.file_analyzer = file_analyzer

    def start_file_analyzer(self, path):
        result = self.file_analyzer.get_metadata(path)
        self.ui.metadataDebug.setPlainText(result)

    def get_file_type(self, path):
        return self.file_analyzer.get_file_type(path)
