"""Tests for the shared file drop widget."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSize, Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout  # noqa: E402

from src.ui.drop_widget import DropWidget  # noqa: E402
from src.ui.theme import current_theme, get_palette  # noqa: E402

_app = QApplication.instance() or QApplication([])


class DropWidgetTest(unittest.TestCase):
    def test_icon_is_120px_and_uses_text_color(self):
        widget = DropWidget()
        layout = QVBoxLayout(widget)
        text = QLabel("Drop file here", widget)
        layout.addWidget(text)
        widget.show()
        _app.processEvents()

        icon = widget.findChild(QLabel, "fileDropIcon")
        self.assertIsNotNone(icon)
        self.assertEqual(icon.size(), QSize(120, 120))
        self.assertEqual(layout.indexOf(icon), 0)
        self.assertFalse(text.isVisible())
        self.assertEqual(layout.alignment(), Qt.AlignmentFlag.AlignCenter)
        self.assertEqual(
            icon.pixmap().toImage().pixelColor(50, 70).name(),
            get_palette(current_theme())["text"].lower(),
        )


if __name__ == "__main__":
    unittest.main()
