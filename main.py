import sys
from pathlib import Path

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QMainWindow

from logger_setup import setup_logging
from src.modules.connectors import setup_domain_connectors, setup_dorking_connectors
from src.modules.domain_analyzer import DomainAnalyzer
from src.controllers.domain_controller import DomainController
from src.controllers.dorking_controller import DorkingController
from src.modules.dorks_search_engine import DorksSearchEngine
from src.modules.google_dorks import GoogleDorksDB

setup_logging()


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        ui_file = Path(__file__).parent / "resources" / "form.ui"
        self.ui = QUiLoader().load(ui_file)
        self.setCentralWidget(self.ui)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        self._load_app_icon()
        self._init_modules()
        self._init_controller()
        self._init_connectors()

    def _load_app_icon(self):
        label = self.ui.appIconLabel
        svg_path = Path(__file__).parent / "resources" / "icon.svg"
        svg_content = svg_path.read_text(encoding="utf-8")
        accent_color = label.palette().color(label.foregroundRole())
        svg_content = svg_content.replace("currentColor", accent_color.name())
        pixmap = QPixmap()
        pixmap.loadFromData(svg_content.encode("utf-8"))
        if not pixmap.isNull():
            pixmap = pixmap.scaled(
                300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            label.setPixmap(pixmap)

    def _init_modules(self):
        logger.debug("Init modules")
        self.dorksSearchEngine = DorksSearchEngine()
        self.googleDorksDB = GoogleDorksDB()

    def _init_controller(self):
        logger.debug("Init controllers")

        self.dorkingController = DorkingController(
            self.ui, self.googleDorksDB, self.dorksSearchEngine
        )
        self.dorkingController.load_categories()

        self.domainAnalyzer = DomainAnalyzer()
        self.domainController = DomainController(self.ui, self.domainAnalyzer)

    def _init_connectors(self):
        setup_dorking_connectors(self.dorkingController)
        setup_domain_connectors(self.domainController)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = MainWindow()

    try:
        with open("resources/style.qss", "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        logger.warning("style.qss not found.")

    widget.show()
    sys.exit(app.exec())
