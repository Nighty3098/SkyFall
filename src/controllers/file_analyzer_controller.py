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

    async def start_file_analyzer(self, path):
        if self.ui.fileMetadataCheck.isChecked():
            self.ui.metadataDebug.setPlainText("Loading...")
            result = await self.file_analyzer.get_metadata(path)
            result += "\n\n"
            result += await self.file_analyzer.check_tail_data(path)
            self.ui.metadataDebug.setPlainText(result)
        
        if self.ui.fileStringsCheck.isChecked():
            self.ui.stringsFileDebug.setPlainText("Loading...")
            strings_result = await self.file_analyzer.get_strings(path)
            self.ui.stringsFileDebug.setPlainText("\n".join(strings_result))

        if self.ui.fileVirustotalCheck.isChecked():
            self.ui.virustotalFileDebug.setPlainText("Loading...")
            virustotal_result = await self.file_analyzer.virustotal_analyze(path)
            self.ui.virustotalFileDebug.setPlainText(virustotal_result)

    def get_file_type(self, path):
        return self.file_analyzer.get_file_type(path)
