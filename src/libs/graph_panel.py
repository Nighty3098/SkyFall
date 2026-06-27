import os

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDockWidget,
    QFormLayout,
    QGroupBox,
    QLabel,
    QListWidget,
    QVBoxLayout,
    QWidget,
)


class PropertiesPanel(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Properties", parent)
        self.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea
        )

        self._node = None
        widget = QWidget()
        layout = QVBoxLayout(widget)

        info_group = QGroupBox("Node Info")
        info_layout = QFormLayout()

        self.title_label = QLabel("-")
        self.type_label = QLabel("-")
        self.id_label = QLabel("-")

        info_layout.addRow("Title:", self.title_label)
        info_layout.addRow("Type:", self.type_label)
        info_layout.addRow("ID:", self.id_label)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        evidence_group = QGroupBox("Evidence")
        evidence_layout = QVBoxLayout()
        self.evidence_list = QListWidget()
        self.evidence_list.itemDoubleClicked.connect(self._open_evidence)
        evidence_layout.addWidget(self.evidence_list)
        evidence_group.setLayout(evidence_layout)
        layout.addWidget(evidence_group)

        layout.addStretch()
        self.setWidget(widget)

    def show_node(self, node):
        self._node = node
        self.title_label.setText(node.title)
        self.type_label.setText(node.entity_type)
        self.id_label.setText(node.id[:8] + "...")

        self.evidence_list.clear()
        for ev in node.evidence:
            label = os.path.basename(ev) if os.path.exists(ev) else ev
            self.evidence_list.addItem(f"{label}\n{ev}")

    def clear(self):
        self._node = None
        self.title_label.setText("-")
        self.type_label.setText("-")
        self.id_label.setText("-")
        self.evidence_list.clear()

    def _open_evidence(self, item):
        path = item.text().split("\n", 1)[-1]
        url = QUrl.fromLocalFile(path) if os.path.exists(path) else QUrl(path)
        QDesktopServices.openUrl(url)
