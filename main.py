import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtUiTools import QUiLoader
from pathlib import Path

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        ui_file = Path(__file__).parent / "resources" / "form.ui"
        self.ui = QUiLoader().load(ui_file)
        self.setCentralWidget(self.ui)
        self.setMinimumSize(800, 500)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self._load_app_icon()

    def _load_app_icon(self):
        label = self.ui.appIconLabel
        svg_path = Path(__file__).parent / "resources" / "icon.svg"
        svg_content = svg_path.read_text(encoding="utf-8")
        accent_color = label.palette().color(label.foregroundRole())
        svg_content = svg_content.replace("currentColor", accent_color.name())
        pixmap = QPixmap()
        pixmap.loadFromData(svg_content.encode("utf-8"))
        if not pixmap.isNull():
            pixmap = pixmap.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(pixmap)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = MainWindow()

    try:
        with open("resources/style.qss", "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("Warning: style.qss not found.")

    widget.show()
    sys.exit(app.exec())
