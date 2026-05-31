from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QCursor

from loguru import logger

def open_dorks_list_menu(listWidget, customDorkEdit, position = None):
    position = listWidget.mapFromGlobal(QCursor.pos())
    item = listWidget.itemAt(position)
    if item is not None:
        menu = QMenu()

        action_edit = menu.addAction("Move to edit")

        global_position = listWidget.viewport().mapToGlobal(position)
        selected_action = menu.exec(global_position)

        if selected_action == action_edit:
            logger.debug(f"Editing: {item.text()}")
            customDorkEdit.setText(item.text())