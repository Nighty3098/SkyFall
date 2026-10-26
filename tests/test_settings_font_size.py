import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QSpinBox, QWidget

from src.controllers import settings_controller
from src.ui.output_formatter import render_html
from src.ui.theme import apply_theme, build_stylesheet, current_font_size

_app = QApplication.instance() or QApplication([])


class FontSizeSettingsTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_file = Path(self.temp_dir.name) / "settings.json"
        self.patches = (
            mock.patch.object(settings_controller, "CONFIG_FILE", self.config_file),
            mock.patch.object(settings_controller, "ensure_config_dir"),
            mock.patch.object(settings_controller, "restrict_file"),
            mock.patch.object(
                settings_controller, "encrypt_settings", side_effect=lambda data: data
            ),
            mock.patch.object(
                settings_controller, "decrypt_settings", side_effect=lambda data: data
            ),
        )
        for patcher in self.patches:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patches):
            patcher.stop()
        self.temp_dir.cleanup()
        apply_theme("dark", font_size=10, app=_app)

    def _ui(self):
        ui = QWidget()
        ui.fontSizeSpinBox = QSpinBox(ui)
        ui.fontSizeSpinBox.setRange(8, 24)
        return ui

    def test_font_size_is_saved_loaded_and_applied(self):
        ui = self._ui()
        settings = settings_controller.Settings(ui)
        ui.fontSizeSpinBox.setValue(16)

        settings.save()

        saved = json.loads(self.config_file.read_text(encoding="utf-8"))
        self.assertEqual(saved["font_size_pt"], 16)
        self.assertEqual(current_font_size(_app), 16)
        self.assertIn("font-size: 16pt", _app.styleSheet())
        self.assertIn("font-size:16pt", render_html("Header\n  value: shown"))

        reloaded_ui = self._ui()
        reloaded = settings_controller.Settings(reloaded_ui)
        self.assertEqual(reloaded.font_size_pt, 16)
        self.assertEqual(reloaded_ui.fontSizeSpinBox.value(), 16)

    def test_stylesheet_uses_one_font_size_for_all_text_tokens(self):
        stylesheet = build_stylesheet(font_size=18)

        self.assertIn("font-size: 18pt", stylesheet)
        self.assertNotIn("font-size: 9pt", stylesheet)
        self.assertNotIn("font-size: 50px", stylesheet)
        self.assertIn("QLabel#winTitle", stylesheet)
        self.assertIn("font-size: 120px", stylesheet)
        self.assertNotIn("font-size: 200px", stylesheet)

    def test_invalid_saved_font_size_uses_default(self):
        self.config_file.write_text('{"font_size_pt": "invalid"}', encoding="utf-8")

        ui = self._ui()
        settings = settings_controller.Settings(ui)

        self.assertEqual(settings.font_size_pt, 10)
        self.assertEqual(ui.fontSizeSpinBox.value(), 10)


if __name__ == "__main__":
    unittest.main()
