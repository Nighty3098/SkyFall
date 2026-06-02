from PySide6.QtCore import QObject
from PySide6.QtGui import QShortcut, QKeySequence

class ShortcutManager(QObject):
    def __init__(self, parent=None, tabWidget=None):
        super().__init__(parent)

        self._tabWidget = tabWidget
        self.shortcut = QShortcut(QKeySequence("Ctrl+O"), parent, self.on_activated)


    def on_activated(self):
        print("")
