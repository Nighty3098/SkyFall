from PySide6.QtWidgets import QTextBrowser

from src.ui.output_formatter import render_html


def is_rich_output_widget(class_name: str, name: str) -> bool:
    is_output_class = class_name in {"QPlainTextEdit", "QTextBrowser"}
    is_output_name = name.endswith("Debug") or name in {"dorksResult", "cameraInfoText"}
    return is_output_class and is_output_name


class RichOutputBrowser(QTextBrowser):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._source_text = ""

    def setPlainText(self, text: str) -> None:  # noqa: N802
        self.set_output_text(text)

    def set_output_text(self, text: str) -> None:
        self._source_text = text
        self.setHtml(render_html(text))

    def setText(self, text: str) -> None:  # noqa: N802
        self.setPlainText(text)

    def toPlainText(self) -> str:  # noqa: N802
        return self._source_text

    def appendPlainText(self, text: str) -> None:  # noqa: N802
        scrollbar = self.verticalScrollBar()
        was_at_bottom = scrollbar.value() >= scrollbar.maximum()
        current = self._source_text
        self.setPlainText(f"{current}\n{text}" if current else text)
        if was_at_bottom:
            scrollbar.setValue(scrollbar.maximum())
