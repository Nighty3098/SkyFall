import json
import os
import stat
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger
from PySide6.QtWidgets import QMessageBox

from src.security import (
    SettingsEncryptionError,
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
    "shodan_api_key": "",
    "numverify_api_key": "",
    "abstractapi_api_key": "",
    "trongrid_api_key": "",
    "etherscan_api_key": "",
    "bscscan_api_key": "",
    "tonapi_api_key": "",
    "helius_api_key": "",
    "abuseipdb_api_key": "",
    "greynoise_api_key": "",
    "whoisfreaks_api_key": "",
    "ipgeolocation_api_key": "",
    "ip2locationio_api_key": "",
    "leakcheck_api_key": "",
    "dehashed_email": "",
    "dehashed_api_key": "",
    "firms_map_key": "",
    "reddit_client_id": "",
    "reddit_client_secret": "",
    "light_theme": False,
    "font_size_pt": 10,
    "frameless_window": True,
    "use_system_proxy": False,
    "telegram_use_proxy": False,
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
    "shodan_api_key": "shodanApiKeyEdit",
    "numverify_api_key": "numverifyApiKeyEdit",
    "abstractapi_api_key": "abstractapiApiKeyEdit",
    "trongrid_api_key": "trongridApiKeyEdit",
    "etherscan_api_key": "etherscanApiKeyEdit",
    "bscscan_api_key": "bscscanApiKeyEdit",
    "tonapi_api_key": "tonapiApiKeyEdit",
    "helius_api_key": "heliusApiKeyEdit",
    "abuseipdb_api_key": "abuseipdbApiKeyEdit",
    "greynoise_api_key": "greynoiseApiKeyEdit",
    "whoisfreaks_api_key": "whoisfreaksApiKeyEdit",
    "ipgeolocation_api_key": "ipgeolocationApiKeyEdit",
    "ip2locationio_api_key": "ip2locationioApiKeyEdit",
    "leakcheck_api_key": "leakcheckApiKeyEdit",
    "dehashed_email": "dehashedEmailEdit",
    "dehashed_api_key": "dehashedApiKeyEdit",
    "firms_map_key": "firmsMapKeyEdit",
    "reddit_client_id": "redditClientIdEdit",
    "reddit_client_secret": "redditClientSecretEdit",
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
        self.shodan_api_key = ""
        self.numverify_api_key = ""
        self.abstractapi_api_key = ""
        self.trongrid_api_key = ""
        self.etherscan_api_key = ""
        self.bscscan_api_key = ""
        self.tonapi_api_key = ""
        self.helius_api_key = ""
        self.abuseipdb_api_key = ""
        self.greynoise_api_key = ""
        self.whoisfreaks_api_key = ""
        self.ipgeolocation_api_key = ""
        self.ip2locationio_api_key = ""
        self.leakcheck_api_key = ""
        self.dehashed_email = ""
        self.dehashed_api_key = ""
        self.firms_map_key = ""
        self.reddit_client_id = ""
        self.reddit_client_secret = ""
        self.light_theme = False
        self.font_size_pt = 10
        self.frameless_window = True
        self.use_system_proxy = False
        self.telegram_use_proxy = False
        self._settings_load_failed = False
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
            self.font_size_pt = self._normalize_font_size(self.font_size_pt)
            self._apply_to_ui()
            restrict_file(CONFIG_FILE)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load settings: {e}")
            self._apply_to_ui()
        except SettingsEncryptionError as exc:
            self._settings_load_failed = True
            logger.error(f"Failed to decrypt settings: {exc}")
            QMessageBox.critical(
                self.ui,
                "Settings Could Not Be Loaded",
                "A saved secret could not be decrypted. Settings will not be "
                "saved until the encryption key is restored.",
            )
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

        use_system_proxy = getattr(self.ui, "useSystemProxyCheck", None)
        if use_system_proxy:
            use_system_proxy.setChecked(self.use_system_proxy)

        telegram_use_proxy = getattr(self.ui, "telegramUseProxyCheck", None)
        if telegram_use_proxy:
            telegram_use_proxy.setChecked(self.telegram_use_proxy)

        mcp_auth = getattr(self.ui, "mcpAuthCheck", None)
        if mcp_auth:
            mcp_auth.setChecked(True)
            mcp_auth.setEnabled(False)

        font_size = getattr(self.ui, "fontSizeSpinBox", None)
        if font_size:
            font_size.setValue(self.font_size_pt)

    def _apply_theme(self):
        apply_theme(
            "light" if self.light_theme else "dark",
            font_size=self.font_size_pt,
        )

    @staticmethod
    def _normalize_font_size(value):
        if isinstance(value, bool):
            return DEFAULT_SETTINGS["font_size_pt"]
        try:
            return max(8, min(24, int(value)))
        except (TypeError, ValueError):
            return DEFAULT_SETTINGS["font_size_pt"]

    def save(self):
        if self._settings_load_failed:
            logger.error(
                "Settings were not saved because stored secrets failed to load"
            )
            QMessageBox.critical(
                self.ui,
                "Settings Not Saved",
                "Restore the settings encryption key before saving settings.",
            )
            return False

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

        use_system_proxy = getattr(self.ui, "useSystemProxyCheck", None)
        if use_system_proxy:
            self.use_system_proxy = use_system_proxy.isChecked()

        telegram_use_proxy = getattr(self.ui, "telegramUseProxyCheck", None)
        if telegram_use_proxy:
            self.telegram_use_proxy = telegram_use_proxy.isChecked()

        font_size = getattr(self.ui, "fontSizeSpinBox", None)
        if font_size:
            self.font_size_pt = self._normalize_font_size(font_size.value())

        try:
            ensure_config_dir()
            data = {key: getattr(self, key) for key in DEFAULT_SETTINGS}
            data = encrypt_settings(data)
        except SettingsEncryptionError as exc:
            logger.error(f"Failed to save settings securely: {exc}")
            QMessageBox.critical(
                self.ui,
                "Settings Not Saved",
                "Sensitive settings could not be encrypted. The existing settings "
                "file was left unchanged.",
            )
            return False
        except OSError as exc:
            logger.error(f"Failed to prepare settings storage: {exc}")
            QMessageBox.critical(
                self.ui,
                "Settings Not Saved",
                "Settings storage is unavailable. The existing settings file was "
                "left unchanged.",
            )
            return False

        temporary_path = None
        try:
            payload = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
            fd, temporary_path = tempfile.mkstemp(
                dir=CONFIG_FILE.parent, prefix=f".{CONFIG_FILE.name}."
            )
            if hasattr(os, "fchmod"):
                os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)
            else:  # pragma: no cover - Windows
                os.chmod(temporary_path, stat.S_IRUSR | stat.S_IWUSR)
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, CONFIG_FILE)
            temporary_path = None
            try:
                directory_fd = os.open(
                    CONFIG_FILE.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
                )
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            except OSError:
                logger.debug("Could not fsync the settings directory")
        except OSError as exc:
            logger.error(f"Failed to save settings atomically: {exc}")
            QMessageBox.critical(
                self.ui,
                "Settings Not Saved",
                "Settings could not be written. The existing settings file was "
                "left unchanged.",
            )
            return False
        finally:
            if temporary_path is not None:
                try:
                    os.unlink(temporary_path)
                except FileNotFoundError:
                    pass

        self._apply_theme()
        for cb in self._post_save_callbacks:
            cb(self)
        logger.success(f"Settings saved to {CONFIG_FILE}")
        return True
