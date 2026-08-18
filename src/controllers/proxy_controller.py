from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow

CONFIG_DIR = Path.home() / ".skyfall"
PROXY_FILE = CONFIG_DIR / "proxies.txt"


class Proxy:
    def __init__(self, ui: "QMainWindow"):
        logger.debug("Init: Proxy")
        self.ui = ui
        self._load_proxies()

    def _load_proxies(self):
        try:
            with open(PROXY_FILE) as proxies_file:
                content = proxies_file.read()
                logger.debug(f"Loaded: {PROXY_FILE}")
                self.ui.proxyListEdit.setPlainText(content)
        except FileNotFoundError:
            logger.error("Proxy file not found")

    def get_proxies_text(self) -> str:
        return self.ui.proxyListEdit.toPlainText()

    def get_proxy_url(self) -> str | None:
        """Return the proxy URL used across the app.

        Returns the system proxy if useSystemProxyCheck is enabled,
        otherwise the first valid proxy from the proxy editor.
        """
        if self.ui.useSystemProxyCheck.isChecked():
            from src.modules.system_proxy import get_system_proxy

            return get_system_proxy()
        return self.get_first_proxy()

    def get_first_proxy(self) -> str | None:
        for line in self.get_proxies_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line
        return None

    def save_proxies(self):
        try:
            with open(PROXY_FILE, "w") as proxies_file:
                logger.debug(f"Saving proxies to: {PROXY_FILE}")
                proxies_file.write(self.ui.proxyListEdit.toPlainText())
        except Exception as e:
            logger.error(f"Saving proxy error: {e}")
