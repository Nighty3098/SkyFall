from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap


def load_app_icon(parent):
    label = parent.ui.appIconLabel
    svg_path = Path(__file__).parent / "../../resources" / "icon.svg"
    svg_content = svg_path.read_text(encoding="utf-8")
    accent_color = label.palette().color(label.foregroundRole())
    svg_content = svg_content.replace("currentColor", accent_color.name())
    pixmap = QPixmap()
    pixmap.loadFromData(svg_content.encode("utf-8"))
    if not pixmap.isNull():
        pixmap = pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(pixmap)


def setup_navbar(parent):
    parent.ui.mainStackedWidget.tabBar().hide()
    parent.ui.menuListWidget.currentRowChanged.connect(
        parent.ui.mainStackedWidget.setCurrentIndex
    )
    tab_count = parent.ui.mainStackedWidget.count()
    tabs = [parent.ui.mainStackedWidget.tabText(i) for i in range(tab_count)]
    parent.ui.menuListWidget.addItems(tabs)
    parent.ui.menuListWidget.setCurrentRow(0)


def setup_ui(self):
    setup_navbar(self)
    load_app_icon(self)
