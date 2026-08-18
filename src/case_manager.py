from datetime import datetime
from pathlib import Path

from loguru import logger
from PySide6.QtWidgets import QFileDialog


class CaseManager:
    CATEGORY_MAP = {
        "serverWhoisDebug": "domains",
        "serverDnsAnalyzeDebug": "domains",
        "serverSubdomainsDebug": "domains",
        "serverLocationDebug": "domains",
        "serverRobotsDebug": "domains",
        "serverTlsDebug": "domains",
        "serverWafDebug": "domains",
        "cookiesDebug": "domains",
        "securityTxtDebug": "domains",
        "socialTagsDebug": "domains",
        "serverNmapDebug": "domains",
        "serverMalwareDebug": "domains",
        "certTrDebug": "domains",
        "telegramDownloaderDebug": "telegram",
        "telegramAnalyzerDebug": "telegram",
        "usernameScriptDebug": "username",
        "maigretDebug": "username",
        "mailSearchDebug": "email",
        "hibpDebug": "email",
        "githubDebug": "github",
        "phoneDebug": "phone",
        "macAddrLocationDebug": "mac",
        "bcDebug": "blockchain",
        "metadataDebug": "files",
        "stringsFileDebug": "files",
        "virustotalFileDebug": "files",
        "LSBDebug": "steganography",
        "spectralAnalysisDebug": "steganography",
        "EOIDebug": "steganography",
        "tailDataDetectionDebug": "steganography",
        "aiReportDebug": "reports",
        "dorksResult": "dorking",
        "downloadFileDebug": "downloads",
    }

    def __init__(self, menu=None):
        self.current_case_path: Path | None = None
        self.current_case_name: str = ""
        self._last_saved: dict[str, str] = {}
        self._current_files: dict[str, Path] = {}
        self._menu = menu

    def create_case(self):
        path_str = QFileDialog.getExistingDirectory(
            None, "Create New Case \u2014 select or create a folder"
        )
        if not path_str:
            return
        path = Path(path_str)
        self.current_case_path = path
        self.current_case_name = path.name
        self._last_saved.clear()
        self._current_files.clear()
        self._ensure_structure()
        self._update_menu_title()
        logger.info(f"Case created: {self.current_case_name} ({path})")

    def open_case(self):
        path_str = QFileDialog.getExistingDirectory(None, "Open Case Folder")
        if not path_str:
            return
        path = Path(path_str)
        self.current_case_path = path
        self.current_case_name = path.name
        self._last_saved.clear()
        self._current_files.clear()
        self._ensure_structure()
        self._update_menu_title()
        logger.info(f"Case opened: {self.current_case_name} ({path})")

    def _update_menu_title(self):
        if self._menu is None:
            return
        if self.current_case_name:
            self._menu.setTitle(self.current_case_name)
        else:
            self._menu.setTitle(" SkyFall")

    def _ensure_structure(self):
        if not self.current_case_path:
            return
        categories = set(self.CATEGORY_MAP.values()) | {"graph", "downloads"}
        for cat in categories:
            (self.current_case_path / cat).mkdir(parents=True, exist_ok=True)

    def get_graph_dir(self) -> str:
        if self.current_case_path:
            path = self.current_case_path / "graph"
            path.mkdir(parents=True, exist_ok=True)
            return str(path)
        return str(Path.home() / ".skyfall" / "data")

    def get_reports_dir(self) -> str:
        if self.current_case_path:
            path = self.current_case_path / "reports"
            path.mkdir(parents=True, exist_ok=True)
            return str(path)
        return str(Path.home() / ".skyfall" / "data")

    def get_downloads_dir(self) -> str:
        if self.current_case_path:
            path = self.current_case_path / "downloads"
            path.mkdir(parents=True, exist_ok=True)
            return str(path)
        fallback = Path.home() / ".skyfall" / "data" / "downloads"
        fallback.mkdir(parents=True, exist_ok=True)
        return str(fallback)

    def save_result(self, widget_name: str, content: str):
        if not self.current_case_path or not content.strip():
            return

        last = self._last_saved.get(widget_name, "")
        if last == content:
            return

        category = self.CATEGORY_MAP.get(widget_name)
        if not category:
            return

        if last and content.startswith(last) and len(content) > len(last):
            filepath = self._current_files.get(widget_name)
            if filepath and filepath.exists():
                filepath.write_text(content, encoding="utf-8")
                self._last_saved[widget_name] = content
                return

        label = widget_name.removesuffix("Debug")
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{timestamp}_{label}.md"

        case_dir = self.current_case_path / category
        case_dir.mkdir(parents=True, exist_ok=True)

        filepath = case_dir / filename
        filepath.write_text(content, encoding="utf-8")
        self._last_saved[widget_name] = content
        self._current_files[widget_name] = filepath
