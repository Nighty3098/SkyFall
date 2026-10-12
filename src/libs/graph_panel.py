from typing import override

from PySide6.QtCore import QMimeData, QSize, Qt
from PySide6.QtGui import QColor, QDrag, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QListWidget, QListWidgetItem

from src.libs.graph_lib import (
    ENTITY_COLORS,
    ENTITY_DESCRIPTIONS,
    ENTITY_NAMES,
    ENTITY_SYMBOLS,
    _ui_font,
)


def _swatch(color: str) -> QPixmap:
    """Small rounded colour chip used as the palette item icon."""
    pix = QPixmap(14, 14)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(1, 1, 12, 12, 4, 4)
    painter.fillPath(path, QColor(color))
    painter.end()
    return pix


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
            item.setData(Qt.ItemDataRole.DecorationRole, _swatch(ENTITY_COLORS[etype]))
            item.setSizeHint(QSize(0, 26))
            item.setToolTip(
                f"{etype} \u2014 {ENTITY_DESCRIPTIONS.get(etype, '')}\n"
                "Drag onto the canvas to create a node."
            )
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
        accent = QColor(ENTITY_COLORS.get(etype, pal["border"]))
        pix = QPixmap(140, 30)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0.5, 0.5, 139, 29, 6, 6)
        painter.fillPath(path, QColor(bg))
        painter.setPen(QColor(pal["border"]))
        painter.drawPath(path)
        painter.setClipPath(path)
        painter.fillRect(0, 0, 4, 30, accent)
        painter.setClipping(False)
        painter.setPen(QColor(text))
        painter.setFont(_ui_font(9, bold=True))
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, etype)
        painter.end()
        drag.setPixmap(pix)
        drag.setHotSpot(pix.rect().center())
        drag.exec(Qt.DropAction.CopyAction)
