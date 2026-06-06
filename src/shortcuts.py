from PySide6.QtCore import QObject
from PySide6.QtGui import QKeySequence, QShortcut


class ShortcutManager(QObject):
    def __init__(self, parent=None, tab_widget=None, menu_list_widget=None):
        super().__init__(parent)

        self._tab_widget = tab_widget
        self._menu_list_widget = menu_list_widget
        self.shortcut = QShortcut(
            QKeySequence("Ctrl+Tab"), parent, self.change_tab_forward
        )
        self.shortcut = QShortcut(
            QKeySequence("Ctrl+Shift+Tab"), parent, self.change_tab_backward
        )

    def change_tab_forward(self):
        num_tabs = self._tab_widget.count()
        current_index = self._tab_widget.currentIndex()

        if current_index + 1 >= num_tabs:
            self._tab_widget.setCurrentIndex(0)
            self._menu_list_widget.setCurrentRow(0)
        else:
            self._tab_widget.setCurrentIndex(current_index + 1)
            self._menu_list_widget.setCurrentRow(current_index + 1)

    def change_tab_backward(self):
        num_tabs = self._tab_widget.count()
        current_index = self._tab_widget.currentIndex()

        if current_index - 1 < 0:
            self._tab_widget.setCurrentIndex(num_tabs - 1)
            self._menu_list_widget.setCurrentRow(num_tabs - 1)
        else:
            self._tab_widget.setCurrentIndex(current_index - 1)
            self._menu_list_widget.setCurrentRow(current_index - 1)
