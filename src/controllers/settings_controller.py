import json
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from src.security import (
    decrypt_settings,
    encrypt_settings,
    ensure_config_dir,
    restrict_file,
)
from src.ui.theme import apply_theme

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
    "hibp_api_key": "",
    "virustotal_api_key": "",
    "google_safe_api_key": "",
    "ipinfo_api_key": "",
    "github_token": "",
    "numverify_api_key": "",
    "abstractapi_api_key": "",
    "trongrid_api_key": "",
    "etherscan_api_key": "",
    "bscscan_api_key": "",
    "tonapi_api_key": "",
    "helius_api_key": "",
    "abuseipdb_api_key": "",
    "greynoise_api_key": "",
    "leakcheck_api_key": "",
    "dehashed_email": "",
    "dehashed_api_key": "",
    "firms_map_key": "",
    "light_theme": False,
    "frameless_window": True,
    "mcp_require_auth": False,
}

FIELD_MAP = {
    "path_to_storage": "pathToStorageEdit",
    "tg_api_key": "tgApiKeyEdit",
    "telegram_api_hash": "telegramApiHashEdit",
    "telegram_phone": "telegramPhoneEdit",
    "intelligent_x_api_key": "intelligentXApiKeyEdit",
    "hibp_api_key": "hibpApiKeyEdit",
    "virustotal_api_key": "virustotalApiKeyEdit",
    "google_safe_api_key": "googleSafeApiKeyEdit",
    "ipinfo_api_key": "ipinfoApiKeyEdit",
    "github_token": "githubTokenEdit",
    "numverify_api_key": "numverifyApiKeyEdit",
    "abstractapi_api_key": "abstractapiApiKeyEdit",
    "trongrid_api_key": "trongridApiKeyEdit",
    "etherscan_api_key": "etherscanApiKeyEdit",
    "bscscan_api_key": "bscscanApiKeyEdit",
    "tonapi_api_key": "tonapiApiKeyEdit",
    "helius_api_key": "heliusApiKeyEdit",
    "abuseipdb_api_key": "abuseipdbApiKeyEdit",
    "greynoise_api_key": "greynoiseApiKeyEdit",
    "leakcheck_api_key": "leakcheckApiKeyEdit",
    "dehashed_email": "dehashedEmailEdit",
    "dehashed_api_key": "dehashedApiKeyEdit",
    "firms_map_key": "firmsMapKeyEdit",
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
        self.hibp_api_key = ""
        self.virustotal_api_key = ""
        self.ipinfo_api_key = ""
        self.google_safe_api_key = ""
        self.github_token = ""
        self.numverify_api_key = ""
        self.abstractapi_api_key = ""
        self.trongrid_api_key = ""
        self.etherscan_api_key = ""
        self.bscscan_api_key = ""
        self.tonapi_api_key = ""
        self.helius_api_key = ""
        self.abuseipdb_api_key = ""
        self.greynoise_api_key = ""
        self.leakcheck_api_key = ""
        self.dehashed_email = ""
        self.dehashed_api_key = ""
        self.firms_map_key = ""
        self.light_theme = False
        self.frameless_window = True
        self.mcp_require_auth = False

        self._post_save_callbacks = []

        self._load()
        self._apply_theme()

    def on_save(self, callback):
        self._post_save_callbacks.append(callback)

    def _load(self):
        logger.debug("Loading settings")
        if not CONFIG_FILE.exists():
            logger.warning("Settings file not found, using defaults")
            self._apply_to_ui()
            return

        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            data = decrypt_settings(data)
            for key in DEFAULT_SETTINGS:
                setattr(self, key, data.get(key, DEFAULT_SETTINGS[key]))
            self._apply_to_ui()
            restrict_file(CONFIG_FILE)
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

        frameless = getattr(self.ui, "framelessCheck", None)
        if frameless:
            frameless.setChecked(self.frameless_window)

        mcp_auth = getattr(self.ui, "mcpAuthCheck", None)
        if mcp_auth:
            mcp_auth.setChecked(self.mcp_require_auth)

    def _apply_theme(self):
        apply_theme("light" if self.light_theme else "dark")

    def save(self):
        logger.debug("Saving settings")
        for key, widget_name in FIELD_MAP.items():
            widget = getattr(self.ui, widget_name, None)
            if widget:
                setattr(self, key, widget.text())

        checkbox = getattr(self.ui, "lightThemeCheck", None)
        if checkbox:
            self.light_theme = checkbox.isChecked()

        frameless = getattr(self.ui, "framelessCheck", None)
        if frameless:
            self.frameless_window = frameless.isChecked()

        mcp_auth = getattr(self.ui, "mcpAuthCheck", None)
        if mcp_auth:
            self.mcp_require_auth = mcp_auth.isChecked()

        ensure_config_dir()
        data = {key: getattr(self, key) for key in DEFAULT_SETTINGS}
        data = encrypt_settings(data)
        CONFIG_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        restrict_file(CONFIG_FILE)
        self._apply_theme()
        for cb in self._post_save_callbacks:
            cb(self)
        logger.success("Settings saved")
