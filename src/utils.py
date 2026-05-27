from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QListWidget


def filter_list(list_widget: "QListWidget", filter_text: str):
    for i in range(list_widget.count()):
        item = list_widget.item(i)
        item.setHidden(filter_text.lower() not in item.text().lower())
