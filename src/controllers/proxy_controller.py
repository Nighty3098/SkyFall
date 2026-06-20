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

    def save_proxies(self):
        try:
            with open(PROXY_FILE, "w") as proxies_file:
                logger.debug(f"Saving proxies to: {PROXY_FILE}")
                proxies_file.write(self.ui.proxyListEdit.toPlainText())
        except Exception as e:
            logger.error(f"Saving proxy error: {e}")
