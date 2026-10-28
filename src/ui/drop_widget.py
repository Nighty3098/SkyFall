from PySide6.QtCore import QByteArray, QEvent, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QFrame, QLabel

from src.ui.theme import RESOURCES_DIR, current_theme, get_palette


class DropWidget(QFrame):
    file_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.file_path = ""
        self.setAcceptDrops(True)
        self.setAutoFillBackground(True)

        self._icon_label = QLabel(self)
        self._icon_label.setObjectName("fileDropIcon")
        self._icon_label.setFixedSize(120, 120)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._icon_added_to_layout = False
        self._icon_svg = (RESOURCES_DIR / "file_drop.svg").read_bytes()
        self._update_icon()

    def showEvent(self, event):
        layout = self.layout()
        if layout is not None and not self._icon_added_to_layout:
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.insertWidget(0, self._icon_label, 0, Qt.AlignmentFlag.AlignCenter)
            self._icon_added_to_layout = True
        for label in self.findChildren(QLabel):
            if label is not self._icon_label:
                label.hide()
        super().showEvent(event)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (
            QEvent.Type.PaletteChange,
            QEvent.Type.StyleChange,
        ):
            self._update_icon()

    def _update_icon(self):
        renderer = QSvgRenderer(QByteArray(self._icon_svg))
        if not renderer.isValid():
            raise RuntimeError("Unable to load resources/file_drop.svg")

        pixmap = QPixmap(120, 120)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        app = QApplication.instance()
        theme = current_theme(app)
        painter.fillRect(pixmap.rect(), QColor(get_palette(theme)["text"]))
        painter.end()
        self._icon_label.setPixmap(pixmap)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            self.file_path = url.toLocalFile()
            self.file_dropped.emit(self.file_path)

    def get_file_path(self):
        return self.file_path
