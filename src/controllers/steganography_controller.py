from typing import TYPE_CHECKING

from loguru import logger

from src.ui.output_formatter import error, info

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

    from src.modules.steganography import SteganographyAnalyzer


class SteganographyController:
    def __init__(
        self,
        ui: "QMainWindow",
        steganography: "SteganographyAnalyzer",
    ):
        logger.debug("Init: SteganographyController")
        self.ui = ui
        self.steganography = steganography

    async def start_steganography_analysis(self, path: str):
        if not path:
            self.ui.LSBDebug.setPlainText(error("No file selected."))
            return

        self.ui.LSBDebug.setPlainText(info("Loading..."))
        self.ui.spectralAnalysisDebug.setPlainText(info("Loading..."))
        self.ui.EOIDebug.setPlainText(info("Loading..."))
        self.ui.tailDataDetectionDebug.setPlainText(info("Loading..."))
        ela_widget = getattr(self.ui, "elaDebug", None)
        if ela_widget is not None:
            ela_widget.setPlainText(info("Loading..."))

        try:
            results = await self.steganography.run_full_analysis(path)
            self.ui.LSBDebug.setPlainText(results.get("lsb", ""))
            self.ui.spectralAnalysisDebug.setPlainText(results.get("spectral", ""))
            self.ui.EOIDebug.setPlainText(results.get("eoi", ""))
            self.ui.tailDataDetectionDebug.setPlainText(results.get("tail", ""))
            if ela_widget is not None:
                ela_widget.setPlainText(results.get("ela", ""))
        except Exception as e:
            err = error(f"Analysis failed: {e}")
            self.ui.LSBDebug.setPlainText(err)
            self.ui.spectralAnalysisDebug.setPlainText(err)
            self.ui.EOIDebug.setPlainText(err)
            self.ui.tailDataDetectionDebug.setPlainText(err)
            if ela_widget is not None:
                ela_widget.setPlainText(err)
