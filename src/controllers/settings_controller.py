import json
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

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
    "ipinfo_api_key": "",
}

FIELD_MAP = {
    "path_to_storage": "pathToStorageEdit",
    "tg_api_key": "tgApiKeyEdit",
    "telegram_api_hash": "telegramApiHashEdit",
    "telegram_phone": "telegramPhoneEdit",
    "intelligent_x_api_key": "intelligentXApiKeyEdit",
    "virustotal_api_key": "virustotalApiKeyEdit",
    "ipinfo_api_key": "ipinfoApiKeyEdit",
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

        self._load()

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

    def save(self):
        logger.debug("Saving settings")
        for key, widget_name in FIELD_MAP.items():
            widget = getattr(self.ui, widget_name, None)
            if widget:
                setattr(self, key, widget.text())

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {key: getattr(self, key) for key in DEFAULT_SETTINGS}
        CONFIG_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.success("Settings saved")
