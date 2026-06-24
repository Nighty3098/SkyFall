import json
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow


CONFIG_DIR = Path.home() / ".skyfall"
CONFIG_FILE = CONFIG_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "path_to_storage": "",
    "tg_api_key": "",
    "telegram_api_hash": "",
    "telegram_phone": "",
    "intelligent_x_api_key": "",
    "virustotal_api_key": "",
    "google_safe_api_key": "",
    "ipinfo_api_key": "",
    "github_token": "",
    "numverify_api_key": "",
    "abstractapi_api_key": "",
    "light_theme": False,
}

FIELD_MAP = {
    "path_to_storage": "pathToStorageEdit",
    "tg_api_key": "tgApiKeyEdit",
    "telegram_api_hash": "telegramApiHashEdit",
    "telegram_phone": "telegramPhoneEdit",
    "intelligent_x_api_key": "intelligentXApiKeyEdit",
    "virustotal_api_key": "virustotalApiKeyEdit",
    "google_safe_api_key": "googleSafeApiKeyEdit",
    "ipinfo_api_key": "ipinfoApiKeyEdit",
    "github_token": "githubTokenEdit",
    "numverify_api_key": "numverifyApiKeyEdit",
    "abstractapi_api_key": "abstractapiApiKeyEdit",
}


class Settings:
    def __init__(self, ui: "QMainWindow"):
        logger.debug("Init: Settings")
        self.ui = ui

        self.path_to_storage = ""
        self.tg_api_key = ""
        self.telegram_api_hash = ""
        self.telegram_phone = ""
        self.intelligent_x_api_key = ""
        self.virustotal_api_key = ""
        self.ipinfo_api_key = ""
        self.google_safe_api_key = ""
        self.github_token = ""
        self.numverify_api_key = ""
        self.abstractapi_api_key = ""
        self.light_theme = False

        self._load()
        self._apply_theme()

    def _load(self):
        logger.debug("Loading settings")
        if not CONFIG_FILE.exists():
            logger.warning("Settings file not found, using defaults")
            self._apply_to_ui()
            return

        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            for key in DEFAULT_SETTINGS:
                setattr(self, key, data.get(key, DEFAULT_SETTINGS[key]))
            self._apply_to_ui()
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load settings: {e}")
            self._apply_to_ui()

    def _apply_to_ui(self):
        for key, widget_name in FIELD_MAP.items():
            widget = getattr(self.ui, widget_name, None)
            if widget:
                widget.setText(getattr(self, key, ""))

        checkbox = getattr(self.ui, "lightThemeCheck", None)
        if checkbox:
            checkbox.setChecked(self.light_theme)

    def _apply_theme(self):
        theme = "style_light.qss" if self.light_theme else "style.qss"
        qss_path = Path(__file__).parent.parent.parent / "resources" / theme
        app = QApplication.instance()
        if app is None:
            return
        try:
            app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            logger.warning(f"{qss_path} not found, using default theme")

        icon_color = "#3A3A3A" if self.light_theme else "#C1C1C1"
        self.ui.appIconLabel.setStyleSheet(f"color: {icon_color};")
        self._reload_icon(icon_color)

    def _reload_icon(self, color):
        svg_path = Path(__file__).parent.parent.parent / "resources" / "icon.svg"
        try:
            svg_content = svg_path.read_text(encoding="utf-8")
            svg_content = svg_content.replace("currentColor", color)
            pixmap = QPixmap()
            pixmap.loadFromData(svg_content.encode("utf-8"))
            if not pixmap.isNull():
                pixmap = pixmap.scaled(
                    300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.ui.appIconLabel.setPixmap(pixmap)
        except (FileNotFoundError, OSError):
            logger.warning("Failed to reload icon")

    def save(self):
        logger.debug("Saving settings")
        for key, widget_name in FIELD_MAP.items():
            widget = getattr(self.ui, widget_name, None)
            if widget:
                setattr(self, key, widget.text())

        checkbox = getattr(self.ui, "lightThemeCheck", None)
        if checkbox:
            self.light_theme = checkbox.isChecked()

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {key: getattr(self, key) for key in DEFAULT_SETTINGS}
        CONFIG_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self._apply_theme()
        logger.success("Settings saved")
