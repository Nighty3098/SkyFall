from PySide6.QtCore import QObject
from PySide6.QtGui import QKeySequence, QShortcut


class ShortcutManager(QObject):
    def __init__(self, parent=None, tab_widget=None):
        super().__init__(parent)

        self._tab_widget = tab_widget
        self.shortcut = QShortcut(QKeySequence("Ctrl+O"), parent, self.on_activated)

    def on_activated(self):
        print("")
