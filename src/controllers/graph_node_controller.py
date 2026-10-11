import os
from typing import TYPE_CHECKING

from PySide6.QtCore import QUrl
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QPushButton,
    QVBoxLayout,
)

from src.libs.graph_lib import ENTITY_NAMES

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow


def _center_dialog(dialog):
    screen = QApplication.primaryScreen()
    if not screen:
        return
    sg = screen.availableGeometry()
    dialog.adjustSize()
    dialog.move(
        sg.center().x() - dialog.width() // 2,
        sg.center().y() - dialog.height() // 2,
    )


class GraphNodeController:
    def __init__(self, ui: "QMainWindow"):
        self.ui = ui
        self._current_node = None

    def show_node(self, node):
        if node is None:
            self.clear()
            return
        self._current_node = node
        self.ui.nodeTitleEdit.blockSignals(True)
        self.ui.nodeTitleEdit.setText(node.title)
        self.ui.nodeTitleEdit.blockSignals(False)
        self.ui.nodeTypeCombo.blockSignals(True)
        idx = (
            ENTITY_NAMES.index(node.entity_type)
            if node.entity_type in ENTITY_NAMES
            else 0
        )
        self.ui.nodeTypeCombo.setCurrentIndex(idx)
        self.ui.nodeTypeCombo.blockSignals(False)
        self.ui.nodeContentEdit.blockSignals(True)
        self.ui.nodeContentEdit.setPlainText(node.content)
        self.ui.nodeContentEdit.blockSignals(False)
        self.ui.nodeEvidenceList.clear()
        for ev in node.evidence:
            label = os.path.basename(ev) if os.path.exists(ev) else ev
            self.ui.nodeEvidenceList.addItem(f"{label}\n{ev}")

    def clear(self):
        self._current_node = None
        self.ui.nodeTitleEdit.blockSignals(True)
        self.ui.nodeTitleEdit.setText("")
        self.ui.nodeTitleEdit.blockSignals(False)
        self.ui.nodeTypeCombo.blockSignals(True)
        self.ui.nodeTypeCombo.setCurrentIndex(0)
        self.ui.nodeTypeCombo.blockSignals(False)
        self.ui.nodeContentEdit.blockSignals(True)
        self.ui.nodeContentEdit.setPlainText("")
        self.ui.nodeContentEdit.blockSignals(False)
        self.ui.nodeEvidenceList.clear()

    def _on_title_changed(self, text):
        if self._current_node:
            self._current_node.title = text
            self._current_node.update()

    def _on_type_changed(self, text):
        if self._current_node:
            self._current_node.entity_type = text
            self._current_node.prepareGeometryChange()
            self._current_node.update()

    def _on_content_changed(self):
        if self._current_node:
            self._current_node.content = self.ui.nodeContentEdit.toPlainText()
            self._current_node.update()

    def _add_file(self):
        if not self._current_node:
            return
        files, _ = QFileDialog.getOpenFileNames(self.ui, "Select Evidence Files")
        for f in files:
            self._current_node.evidence.append(f)
            self.ui.nodeEvidenceList.addItem(f"{os.path.basename(f)}\n{f}")
        self._current_node._photo_cache.clear()
        self._current_node.update()

    def _add_url(self):
        if not self._current_node:
            return
        from src.ui.theme import dialog_palette

        pal = dialog_palette()
        bg = pal["bg"]
        surface = pal["surface"]
        border = pal["border"]
        text_color = pal["text"]
        radius = pal["radius"]
        dialog = QDialog(self.ui)
        dialog.setWindowTitle("Add URL")
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {text_color};
                border: 1px solid {border};
                border-radius: {radius};
            }}
            QLineEdit {{
                border-radius: {radius};
                border: 1px solid {border};
                background-color: {surface};
                color: {text_color};
                padding: 5px;
            }}
            QPushButton {{
                border-radius: {radius};
                border: 1px solid {border};
                background-color: {surface};
                color: {text_color};
                padding: 6px 16px;
                min-height: 24px;
            }}
            QPushButton:hover {{
                background-color: {border};
            }}
            QPushButton:pressed {{
                background-color: {text_color};
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
        _center_dialog(dialog)
        if dialog.exec() == QDialog.DialogCode.Accepted and line_edit.text().strip():
            url = line_edit.text().strip()
            self._current_node.evidence.append(url)
            self.ui.nodeEvidenceList.addItem(f"{url}\n{url}")
            self._current_node.update()

    def _remove_evidence(self):
        if not self._current_node:
            return
        for item in self.ui.nodeEvidenceList.selectedItems():
            idx = self.ui.nodeEvidenceList.row(item)
            if 0 <= idx < len(self._current_node.evidence):
                del self._current_node.evidence[idx]
            self.ui.nodeEvidenceList.takeItem(idx)
        self._current_node._photo_cache.clear()
        self._current_node.update()

    def _evidence_context_menu(self, pos):
        if not self.ui.nodeEvidenceList.itemAt(pos):
            return
        menu = QMenu(self.ui)
        delete_act = QAction("Delete", self.ui)
        delete_act.triggered.connect(self._remove_evidence)
        menu.addAction(delete_act)
        menu.exec(self.ui.nodeEvidenceList.viewport().mapToGlobal(pos))

    def _open_evidence(self, item):
        path = item.text().split("\n", 1)[-1]
        url = QUrl.fromLocalFile(path) if os.path.exists(path) else QUrl(path)
        QDesktopServices.openUrl(url)
