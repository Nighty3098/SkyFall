from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame

class DropWidget(QFrame):
    fileDropped = Signal(str)
    def __init__(self, parent=None):
        super().__init__(parent)

        self.file_path = ""
        self.setAcceptDrops(True)
        self.setAutoFillBackground(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            self.file_path = url.toLocalFile()
            self.fileDropped.emit(self.file_path)

    def getFilePath(self):
        return self.file_path