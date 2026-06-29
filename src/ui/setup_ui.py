from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication


def setup_title_bar(parent):
    ss = QApplication.instance().styleSheet()
    dark = "#0A0A0A" in ss
    traffic_bg = "#1C1C1C" if dark else "#E5E5E5"

    for name, color, hover in [
        ("windowCloseBtn", "#FF5F57", "#FF3B30"),
        ("windowMinimizeBtn", "#FEBC2E", "#F5A623"),
        ("windowMaximizeBtn", "#28C840", "#1CAF2E"),
    ]:
        btn = getattr(parent.ui, name)
        btn.setFixedSize(14, 14)
        btn.setStyleSheet(f"""
            #{name} {{
                background-color: {color};
                border: none;
                border-radius: 7px;
            }}
            #{name}:hover {{
                background-color: {hover};
            }}
        """)

    parent.ui.windowCloseBtn.clicked.connect(parent.close)
    parent.ui.windowMinimizeBtn.clicked.connect(parent.showMinimized)

    def toggle_maximize():
        if parent.isMaximized():
            parent.showNormal()
        else:
            parent.showMaximized()

    parent.ui.windowMaximizeBtn.clicked.connect(toggle_maximize)

    parent._drag_pos = None

    def title_bar_mouse_press(event):
        if event.button() == Qt.MouseButton.LeftButton:
            parent._drag_pos = event.globalPosition().toPoint()

    def title_bar_mouse_move(event):
        if parent._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            if parent.isMaximized():
                parent.showNormal()
            parent.move(
                parent.pos() + event.globalPosition().toPoint() - parent._drag_pos
            )
            parent._drag_pos = event.globalPosition().toPoint()

    def title_bar_mouse_release(event):
        if event.button() == Qt.MouseButton.LeftButton:
            parent._drag_pos = None

    parent.ui.titleBar.mousePressEvent = title_bar_mouse_press
    parent.ui.titleBar.mouseMoveEvent = title_bar_mouse_move
    parent.ui.titleBar.mouseReleaseEvent = title_bar_mouse_release


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
    setup_title_bar(self)
    setup_navbar(self)
    load_app_icon(self)
