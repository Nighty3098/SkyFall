from typing import TYPE_CHECKING

from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QTextEdit

if TYPE_CHECKING:
    from PySide6.QtWidgets import QListWidget


def filter_list(list_widget: "QListWidget", filter_text: str):
    for i in range(list_widget.count()):
        item = list_widget.item(i)
        item.setHidden(filter_text.lower() not in item.text().lower())


def find_text(controller, text):
    widget = controller.ui.dorksResult

    if not text:
        widget.setExtraSelections([])
        return

    extra_selections = []

    fmt = QTextCharFormat()
    fmt.setBackground(QColor("yellow"))

    document = widget.document()
    cursor = QTextCursor(document)

    while True:
        cursor = document.find(text, cursor)

        if cursor.isNull():
            break

        selection = QTextEdit.ExtraSelection()
        selection.format = fmt
        selection.cursor = cursor
        extra_selections.append(selection)

    widget.setExtraSelections(extra_selections)
