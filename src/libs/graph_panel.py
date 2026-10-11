from typing import override

from PySide6.QtCore import QMimeData, Qt
from PySide6.QtGui import QColor, QDrag, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QListWidget, QListWidgetItem

from src.libs.graph_lib import ENTITY_NAMES, ENTITY_SYMBOLS


class EntityPalette(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setMinimumWidth(160)
        self.setSpacing(1)

        for etype in ENTITY_NAMES:
            sym = ENTITY_SYMBOLS.get(etype, "")
            item = QListWidgetItem(f"  {sym}  {etype}")
            item.setData(Qt.ItemDataRole.UserRole, etype)
            self.addItem(item)

    def set_filter(self, text: str):
        text = text.lower().strip()
        for i in range(self.count()):
            item = self.item(i)
            etype = item.data(Qt.ItemDataRole.UserRole)
            item.setHidden(bool(text) and text not in etype.lower())

    @override
    def startDrag(self, supported_actions):
        item = self.currentItem()
        if not item:
            return
        etype = item.data(Qt.ItemDataRole.UserRole)
        mime = QMimeData()
        mime.setText(etype)
        drag = QDrag(self)
        drag.setMimeData(mime)
        from src.ui.theme import dialog_palette

        pal = dialog_palette()
        bg = pal["surface"]
        text = pal["text"]
        pix = QPixmap(120, 28)
        pix.fill(QColor(bg))
        painter = QPainter(pix)
        painter.setPen(QColor(text))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, etype)
        painter.end()
        drag.setPixmap(pix)
        drag.setHotSpot(pix.rect().center())
        drag.exec(Qt.DropAction.CopyAction)
