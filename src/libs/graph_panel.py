import os

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.libs.graph_lib import ENTITY_NAMES


class PropertiesPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(250)

        self._node = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Title")
        self.title_edit.textChanged.connect(self._on_title_changed)
        layout.addWidget(self.title_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(ENTITY_NAMES)
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        layout.addWidget(self.type_combo)

        self.content_edit = QPlainTextEdit()
        self.content_edit.setPlaceholderText("Content")
        self.content_edit.textChanged.connect(self._on_content_changed)
        layout.addWidget(self.content_edit)

        self.evidence_list = QListWidget()
        self.evidence_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.evidence_list.customContextMenuRequested.connect(
            self._evidence_context_menu
        )
        self.evidence_list.itemDoubleClicked.connect(self._open_evidence)
        layout.addWidget(self.evidence_list)

        ev_btn_layout = QHBoxLayout()
        btn_add_file = QPushButton("Add File")
        btn_add_file.clicked.connect(self._add_file)
        btn_add_url = QPushButton("Add URL")
        btn_add_url.clicked.connect(self._add_url)
        btn_remove = QPushButton("Remove")
        btn_remove.clicked.connect(self._remove_evidence)
        ev_btn_layout.addWidget(btn_add_file)
        ev_btn_layout.addWidget(btn_add_url)
        ev_btn_layout.addWidget(btn_remove)
        layout.addLayout(ev_btn_layout)

        layout.addStretch()

    def show_node(self, node):
        if node is None:
            self.clear()
            return
        self._node = node
        self.title_edit.blockSignals(True)
        self.title_edit.setText(node.title)
        self.title_edit.blockSignals(False)
        self.type_combo.blockSignals(True)
        idx = (
            ENTITY_NAMES.index(node.entity_type)
            if node.entity_type in ENTITY_NAMES
            else 0
        )
        self.type_combo.setCurrentIndex(idx)
        self.type_combo.blockSignals(False)
        self.content_edit.blockSignals(True)
        self.content_edit.setPlainText(node.content)
        self.content_edit.blockSignals(False)
        self.evidence_list.clear()
        for ev in node.evidence:
            label = os.path.basename(ev) if os.path.exists(ev) else ev
            self.evidence_list.addItem(f"{label}\n{ev}")

    def clear(self):
        self._node = None
        self.title_edit.blockSignals(True)
        self.title_edit.setText("")
        self.title_edit.blockSignals(False)
        self.type_combo.blockSignals(True)
        self.type_combo.setCurrentIndex(0)
        self.type_combo.blockSignals(False)
        self.content_edit.blockSignals(True)
        self.content_edit.setPlainText("")
        self.content_edit.blockSignals(False)
        self.evidence_list.clear()

    def _on_title_changed(self, text):
        if self._node:
            self._node.title = text
            self._node.update()

    def _on_type_changed(self, text):
        if self._node:
            self._node.entity_type = text
            self._node.prepareGeometryChange()
            self._node.update()

    def _on_content_changed(self):
        if self._node:
            self._node.content = self.content_edit.toPlainText()
            self._node.update()

    def _add_file(self):
        if not self._node:
            return
        files, _ = QFileDialog.getOpenFileNames(self, "Select Evidence Files")
        for f in files:
            self._node.evidence.append(f)
            self.evidence_list.addItem(f"{os.path.basename(f)}\n{f}")
        self._node.update()

    def _add_url(self):
        if not self._node:
            return
        ss = QApplication.instance().styleSheet()
        dark = "#0A0A0A" in ss
        bg = "#0A0A0A" if dark else "#F5F5F5"
        surface = "#161616" if dark else "#E8E8E8"
        border = "#262626" if dark else "#D0D0D0"
        text = "#C1C1C1" if dark else "#3A3A3A"
        dialog = QDialog(self)
        dialog.setWindowTitle("Add URL")
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            QLineEdit {{
                border-radius: 10px;
                border: 1px solid {border};
                background-color: {surface};
                color: {text};
                padding: 5px;
            }}
            QPushButton {{
                border-radius: 10px;
                border: 1px solid {border};
                background-color: {surface};
                color: {text};
                padding: 6px 16px;
                min-height: 24px;
            }}
            QPushButton:hover {{
                background-color: {border};
            }}
            QPushButton:pressed {{
                background-color: {text};
                color: {bg};
            }}
        """)
        dlg_layout = QVBoxLayout(dialog)
        line_edit = QLineEdit()
        line_edit.setPlaceholderText("https://example.com/file.pdf")
        dlg_layout.addWidget(line_edit)
        btn_hlay = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_hlay.addWidget(ok_btn)
        btn_hlay.addWidget(cancel_btn)
        dlg_layout.addLayout(btn_hlay)
        if dialog.exec() == QDialog.DialogCode.Accepted and line_edit.text().strip():
            url = line_edit.text().strip()
            self._node.evidence.append(url)
            self.evidence_list.addItem(f"{url}\n{url}")
            self._node.update()

    def _remove_evidence(self):
        if not self._node:
            return
        for item in self.evidence_list.selectedItems():
            idx = self.evidence_list.row(item)
            if 0 <= idx < len(self._node.evidence):
                del self._node.evidence[idx]
            self.evidence_list.takeItem(idx)
        self._node.update()

    def _evidence_context_menu(self, pos):
        if not self.evidence_list.itemAt(pos):
            return
        menu = QMenu(self)
        delete_act = QAction("Delete", self)
        delete_act.triggered.connect(self._remove_evidence)
        menu.addAction(delete_act)
        menu.exec(self.evidence_list.viewport().mapToGlobal(pos))

    def _open_evidence(self, item):
        path = item.text().split("\n", 1)[-1]
        url = QUrl.fromLocalFile(path) if os.path.exists(path) else QUrl(path)
        QDesktopServices.openUrl(url)
