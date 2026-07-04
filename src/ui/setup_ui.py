from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


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


def setup_case_panel(parent, case_manager):
    layout = parent.ui.horizontalLayout_6

    wrapper = QWidget()
    wrapper.setFixedWidth(150)
    vbox = QVBoxLayout(wrapper)
    vbox.setContentsMargins(4, 4, 4, 4)
    vbox.setSpacing(4)

    panel = QFrame()
    panel_layout = QVBoxLayout(panel)
    panel_layout.setContentsMargins(0, 0, 0, 4)
    panel_layout.setSpacing(4)

    case_label = QLabel(" - ")
    case_label.setAlignment(Qt.AlignHCenter)
    case_label.setStyleSheet("font-weight: bold; font-size: 11px;")
    panel_layout.addWidget(case_label)
    case_manager.register_label(case_label)

    btn_style = """
    QPushButton {
        background: palette(window);
        border: none;
        border-radius: 10px;
        padding: 4px 10px;
        text-align: left;
        color: #888888;
    }
    QPushButton:hover {
        background: palette(midlight);
        color: palette(window-text);
    }
    QPushButton:pressed {
        background: palette(highlight);
        color: palette(highlighted-text);
    }
    """
    btn_row = QVBoxLayout()
    btn_row.setSpacing(4)
    new_btn = QPushButton("New")
    new_btn.setStyleSheet(btn_style)
    open_btn = QPushButton("Open")
    open_btn.setStyleSheet(btn_style)
    btn_row.addWidget(new_btn)
    btn_row.addWidget(open_btn)
    panel_layout.addLayout(btn_row)

    idx = layout.indexOf(parent.ui.menuListWidget)
    layout.removeWidget(parent.ui.menuListWidget)
    vbox.addWidget(parent.ui.menuListWidget, 1)
    vbox.addStretch()
    vbox.addWidget(panel)
    layout.insertWidget(idx, wrapper)

    new_btn.clicked.connect(case_manager.create_case)
    open_btn.clicked.connect(case_manager.open_case)


def setup_ui(self, case_manager=None):
    setup_navbar(self)
    load_app_icon(self)
    if case_manager:
        setup_case_panel(self, case_manager)
