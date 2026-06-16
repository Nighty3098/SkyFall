from loguru import logger
from PySide6.QtWidgets import QMenu


def open_dorks_list_menu(list_widget, custom_dork_edit, position):
    item = list_widget.itemAt(position)
    if item is not None:
        menu = QMenu()

        action_edit = menu.addAction("Move to edit")

        global_position = list_widget.viewport().mapToGlobal(position)
        selected_action = menu.exec(global_position)

        if selected_action == action_edit:
            logger.debug(f"Editing: {item.text()}")
            custom_dork_edit.setText(item.text())
