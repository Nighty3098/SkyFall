from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtWidgets import QFileDialog

from src.modules.case_store import CaseStore


class CaseManager:
    CATEGORY_MAP = {
        "serverWhoisDebug": "domains",
        "serverWhoisHistoryDebug": "domains",
        "serverReverseWhoisDebug": "domains",
        "serverDomainTimelineDebug": "domains",
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
        "domainsOnIpDebug": "domains",
        "serverJsSecretsDebug": "domains",
        "serverThreatIntelDebug": "domains",
        "ip2locationGeoDebug": "domains",
        "ip2locationNetworkDebug": "domains",
        "ip2locationThreatDebug": "domains",
        "telegramDownloaderDebug": "telegram",
        "telegramAnalyzerDebug": "telegram",
        "usernameResultsDebug": "username",
        "mailSearchDebug": "email",
        "hibpDebug": "email",
        "emailHeaderDebug": "email",
        "emailAccountsDebug": "email",
        "socialDebug": "social",
        "redditOsintDebug": "reddit",
        "leakDebug": "leaks",
        "geoDebug": "geo",
        "archiveDebug": "archive",
        "githubDebug": "github",
        "shodanDebug": "shodan",
        "phoneDebug": "phone",
        "macAddrLocationDebug": "mac",
        "wifiDebug": "wifi",
        "bcDebug": "blockchain",
        "metadataDebug": "files",
        "stringsFileDebug": "files",
        "virustotalFileDebug": "files",
        "LSBDebug": "steganography",
        "spectralAnalysisDebug": "steganography",
        "EOIDebug": "steganography",
        "tailDataDetectionDebug": "steganography",
        "elaDebug": "steganography",
        "aiReportDebug": "reports",
        "dorksResult": "dorking",
        "downloadFileDebug": "downloads",
    }

    def __init__(self, menu=None, graph_widget=None):
        self.current_case_path: Path | None = None
        self.current_case_name: str = ""
        self._last_saved: dict[str, str] = {}
        self._current_files: dict[str, Path] = {}
        self._menu = menu
        self._graph_widget = graph_widget
        self._store: CaseStore | None = None

    def create_case(self):
        path_str = QFileDialog.getExistingDirectory(
            None, "Create New Case \u2014 select or create a folder"
        )
        if not path_str:
            return
        self._activate_case(Path(path_str))
        logger.info(
            f"Case created: {self.current_case_name} ({self.current_case_path})"
        )
        return self.current_case_path

    def open_case(self):
        path_str = QFileDialog.getExistingDirectory(None, "Open Case Folder")
        if not path_str:
            return
        self._activate_case(Path(path_str))
        logger.info(f"Case opened: {self.current_case_name} ({self.current_case_path})")
        return self.current_case_path

    def open_case_path(self, path: str | Path) -> Path:
        """Open a case without a file dialog (used by tests and MCP/CLI)."""
        self._activate_case(Path(path).expanduser())
        logger.info(f"Case opened: {self.current_case_name} ({self.current_case_path})")
        return self.current_case_path  # type: ignore[return-value]

    def _activate_case(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        self.current_case_path = path.resolve()
        self.current_case_name = self.current_case_path.name
        self._last_saved.clear()
        self._current_files.clear()
        self._store = None
        self._ensure_structure()
        self._update_menu_title()
        # Create the database eagerly so a freshly opened case already has
        # the unified store ready for notes and the case manager dialog.
        self.case_store.log_activity(
            "case_opened", f"Case opened: {self.current_case_name}"
        )

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
        categories = set(self.CATEGORY_MAP.values()) | {
            "graph",
            "downloads",
            "notes",
            "evidence",
            "screenshots",
            "logs",
            "logs/requests",
            "graph/versions",
        }
        for cat in categories:
            (self.current_case_path / cat).mkdir(parents=True, exist_ok=True)

    @property
    def case_store(self) -> CaseStore:
        """Unified SQLite store for the current case (or the default data dir)."""
        if self._store is None:
            root = self.current_case_path or (Path.home() / ".skyfall" / "data")
            self._store = CaseStore(root)
        return self._store

    def set_graph_widget(self, graph_widget) -> None:
        self._graph_widget = graph_widget

    def _graph_snapshot(self) -> dict[str, Any] | None:
        widget = self._graph_widget
        if widget is None:
            return None
        try:
            return widget.to_dict()
        except Exception:
            logger.exception("Failed to snapshot the graph")
            return None

    def add_note(
        self,
        title: str,
        body: str = "",
        tags: list[str] | str | None = None,
    ) -> dict[str, Any]:
        return self.case_store.create_note(title, body, tags)

    def list_notes(self, limit: int = 500) -> list[dict[str, Any]]:
        return self.case_store.list_notes(limit)

    def get_note(self, note_id: str) -> dict[str, Any] | None:
        return self.case_store.get_note(note_id)

    def update_note(
        self,
        note_id: str,
        title: str | None = None,
        body: str | None = None,
        tags: list[str] | str | None = None,
    ) -> dict[str, Any] | None:
        return self.case_store.update_note(note_id, title, body, tags)

    def delete_note(self, note_id: str) -> bool:
        return self.case_store.delete_note(note_id)

    def attach_file(
        self,
        path: str | Path,
        caption: str = "",
        note_id: str | None = None,
        kind: str = "file",
    ) -> dict[str, Any] | None:
        return self.case_store.add_attachment(
            path, kind=kind, caption=caption, note_id=note_id
        )

    def capture_screenshot(
        self,
        widget=None,
        caption: str = "",
        note_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Capture a widget (the graph canvas by default) into the case."""
        target = widget or self._graph_widget
        if target is None or not hasattr(target, "grab"):
            return None
        pixmap = target.grab()
        if pixmap.isNull():
            return None
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        try:
            if not pixmap.save(buffer, "PNG"):
                return None
            data = bytes(buffer.data())
        finally:
            buffer.close()
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return self.case_store.add_screenshot(
            data,
            caption=caption,
            note_id=note_id,
            filename=f"screenshot_{stamp}.png",
        )

    def log_request(self, module: str, target: str = "", **kwargs) -> dict[str, Any]:
        return self.case_store.log_request(module, target, **kwargs)

    def log_response(self, module: str, target: str, response, duration_ms=None):
        return self.case_store.log_response(
            module, target, response, duration_ms=duration_ms
        )

    def save_graph_version(
        self,
        snapshot: dict[str, Any] | None = None,
        label: str = "",
        action: str = "manual",
        **kwargs,
    ) -> dict[str, Any] | None:
        snapshot = snapshot if snapshot is not None else self._graph_snapshot()
        if snapshot is None:
            return None
        return self.case_store.save_graph_version(
            snapshot, label=label, action=action, **kwargs
        )

    def list_graph_versions(
        self, limit: int = 100, include_snapshot: bool = False
    ) -> list[dict[str, Any]]:
        return self.case_store.list_graph_versions(limit, include_snapshot)

    def get_graph_version(self, version_id: int) -> dict[str, Any] | None:
        return self.case_store.get_graph_version(version_id)

    def restore_graph_version(self, version_id: int) -> dict[str, Any] | None:
        """Load a historical snapshot into the graph (undoable)."""
        version = self.case_store.get_graph_version(version_id)
        if version is None:
            return None
        widget = self._graph_widget
        if widget is not None:
            try:
                widget.push_undo_state()
                widget.from_dict(version.get("snapshot") or {"nodes": [], "edges": []})
                widget.viewport().update()
            except Exception:
                logger.exception("Failed to restore graph version")
                return None
        self.case_store.log_activity(
            "graph_rollback",
            f"Graph rolled back to version {version_id}",
            {"version_id": version_id, "label": version.get("label")},
        )
        return version

    def delete_graph_version(self, version_id: int) -> bool:
        return self.case_store.delete_graph_version(version_id)

    def case_summary(self) -> dict[str, Any]:
        summary = self.case_store.stats()
        summary["name"] = self.current_case_name
        summary["path"] = str(self.current_case_path or self.case_store.root)
        return summary

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
