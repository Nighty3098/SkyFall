"""Case Manager dialog: notes, evidence, request logs and graph history."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.ui.theme import dialog_palette


def _human_size(size: int) -> str:
    value = float(size or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


class CaseDialog(QDialog):
    """Unified workspace for one investigation case."""

    graph_restored = Signal()

    def __init__(self, case_manager, parent=None):
        super().__init__(parent)
        self.case_manager = case_manager
        self._current_note_id: str | None = None
        self._requests: list[dict] = []
        self._versions: list[dict] = []
        self._attachments: list[dict] = []
        self.setWindowTitle("Case Manager")
        self.resize(1000, 680)
        self._build_ui()
        self._apply_theme()
        self.refresh_all()

    # ------------------------------------------------------------------ layout

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.header = QLabel()
        self.header.setWordWrap(True)
        layout.addWidget(self.header)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_notes_tab(), "Notes")
        self.tabs.addTab(self._build_evidence_tab(), "Evidence & screenshots")
        self.tabs.addTab(self._build_requests_tab(), "Raw requests")
        self.tabs.addTab(self._build_versions_tab(), "Graph history")
        layout.addWidget(self.tabs, 1)

        bottom = QHBoxLayout()
        self.stats_label = QLabel()
        bottom.addWidget(self.stats_label)
        bottom.addStretch(1)
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_all)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        bottom.addWidget(refresh_button)
        bottom.addWidget(close_button)
        layout.addLayout(bottom)

    def _build_notes_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.notes_list = QListWidget()
        self.notes_list.currentItemChanged.connect(self._on_note_selected)
        left_layout.addWidget(self.notes_list, 1)
        note_buttons = QHBoxLayout()
        new_button = QPushButton("New")
        new_button.clicked.connect(self._new_note)
        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(self._delete_note)
        note_buttons.addWidget(new_button)
        note_buttons.addWidget(delete_button)
        left_layout.addLayout(note_buttons)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.note_title = QLineEdit()
        self.note_title.setPlaceholderText("Note title")
        self.note_tags = QLineEdit()
        self.note_tags.setPlaceholderText("Tags, comma separated")
        self.note_body = QPlainTextEdit()
        self.note_body.setPlaceholderText(
            "Findings, hypotheses, entity links, collection rationale…"
        )
        right_layout.addWidget(self.note_title)
        right_layout.addWidget(self.note_tags)
        right_layout.addWidget(self.note_body, 1)

        note_actions = QHBoxLayout()
        save_button = QPushButton("Save note")
        save_button.clicked.connect(self._save_note)
        attach_button = QPushButton("Attach file…")
        attach_button.clicked.connect(self._attach_to_note)
        screenshot_button = QPushButton("Capture graph screenshot")
        screenshot_button.clicked.connect(self._capture_note_screenshot)
        note_actions.addWidget(save_button)
        note_actions.addWidget(attach_button)
        note_actions.addWidget(screenshot_button)
        note_actions.addStretch(1)
        right_layout.addLayout(note_actions)
        splitter.addWidget(right)
        splitter.setSizes([280, 680])
        return page

    def _build_evidence_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.evidence_table = QTableWidget(0, 5)
        self.evidence_table.setHorizontalHeaderLabels(
            ["Created", "Kind", "Name", "Size", "Path"]
        )
        self.evidence_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.evidence_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.evidence_table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.Stretch
        )
        self.evidence_table.doubleClicked.connect(self._open_attachment)
        layout.addWidget(self.evidence_table, 1)

        buttons = QHBoxLayout()
        add_button = QPushButton("Add file…")
        add_button.clicked.connect(self._add_attachment)
        open_button = QPushButton("Open")
        open_button.clicked.connect(self._open_attachment)
        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(self._delete_attachment)
        buttons.addWidget(add_button)
        buttons.addWidget(open_button)
        buttons.addWidget(delete_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        return page

    def _build_requests_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        splitter = QSplitter(Qt.Orientation.Vertical)
        self.requests_table = QTableWidget(0, 6)
        self.requests_table.setHorizontalHeaderLabels(
            ["Time", "Module", "Target", "Status", "Duration", "URL"]
        )
        self.requests_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.requests_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.requests_table.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeMode.Stretch
        )
        self.requests_table.itemSelectionChanged.connect(self._show_request_details)
        splitter.addWidget(self.requests_table)
        self.request_details = QPlainTextEdit()
        self.request_details.setReadOnly(True)
        self.request_details.setPlaceholderText(
            "Select a request to see headers, body and the raw log path."
        )
        splitter.addWidget(self.request_details)
        splitter.setSizes([280, 260])
        layout.addWidget(splitter, 1)

        buttons = QHBoxLayout()
        open_raw = QPushButton("Open raw log")
        open_raw.clicked.connect(self._open_raw_log)
        buttons.addWidget(open_raw)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        return page

    def _build_versions_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        splitter = QSplitter(Qt.Orientation.Vertical)
        self.versions_table = QTableWidget(0, 7)
        self.versions_table.setHorizontalHeaderLabels(
            ["ID", "Created", "Label", "Action", "Nodes", "Edges", "Short hash"]
        )
        self.versions_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.versions_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.versions_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.versions_table.itemSelectionChanged.connect(self._show_version_preview)
        splitter.addWidget(self.versions_table)
        self.version_preview = QPlainTextEdit()
        self.version_preview.setReadOnly(True)
        splitter.addWidget(self.version_preview)
        splitter.setSizes([300, 240])
        layout.addWidget(splitter, 1)

        buttons = QHBoxLayout()
        save_button = QPushButton("Save current version…")
        save_button.clicked.connect(self._save_version)
        restore_button = QPushButton("Restore selected")
        restore_button.clicked.connect(self._restore_version)
        delete_button = QPushButton("Delete selected")
        delete_button.clicked.connect(self._delete_version)
        buttons.addWidget(save_button)
        buttons.addWidget(restore_button)
        buttons.addWidget(delete_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        return page

    # ------------------------------------------------------------------ loading

    def refresh_all(self):
        self._refresh_header()
        self._load_notes()
        self._load_attachments()
        self._load_requests()
        self._load_versions()

    def _refresh_header(self):
        manager = self.case_manager
        name = manager.current_case_name or "No case (default data folder)"
        path = manager.current_case_path or manager.case_store.root
        self.header.setText(f"<b>{name}</b><br><span>{path}</span>")
        try:
            stats = manager.case_summary()
            self.stats_label.setText(
                f"{stats['notes']} notes · {stats['attachments']} attachments · "
                f"{stats['requests']} requests · "
                f"{stats['graph_versions']} graph versions"
            )
        except Exception:
            self.stats_label.setText("")

    def _load_notes(self):
        current = self._current_note_id
        self.notes_list.blockSignals(True)
        self.notes_list.clear()
        notes = self.case_manager.list_notes()
        for note in notes:
            tags = ", ".join(note.get("tags") or [])
            suffix = f"  ·  {tags}" if tags else ""
            item = QListWidgetItem(f"{note.get('title') or 'Untitled'}{suffix}")
            item.setData(Qt.ItemDataRole.UserRole, note["id"])
            item.setToolTip((note.get("body") or "")[:500])
            self.notes_list.addItem(item)
        self.notes_list.blockSignals(False)
        if current:
            for index in range(self.notes_list.count()):
                item = self.notes_list.item(index)
                if item.data(Qt.ItemDataRole.UserRole) == current:
                    self.notes_list.setCurrentItem(item)
                    break

    def _load_attachments(self):
        self._attachments = self.case_manager.case_store.list_attachments(limit=1000)
        self.evidence_table.setRowCount(len(self._attachments))
        for row, attachment in enumerate(self._attachments):
            values = [
                (attachment.get("created_at") or "").replace("T", " "),
                attachment.get("kind") or "",
                attachment.get("original_name") or "",
                _human_size(int(attachment.get("size") or 0)),
                attachment.get("path") or "",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, attachment.get("id"))
                self.evidence_table.setItem(row, column, item)

    def _load_requests(self):
        self._requests = self.case_manager.case_store.list_requests(limit=500)
        self.requests_table.setRowCount(len(self._requests))
        for row, request in enumerate(self._requests):
            values = [
                (request.get("created_at") or "").replace("T", " "),
                request.get("module") or "",
                request.get("target") or "",
                str(request.get("status_code") or ""),
                f"{request['duration_ms']:.0f} ms"
                if request.get("duration_ms") is not None
                else "",
                request.get("url") or "",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, request.get("id"))
                self.requests_table.setItem(row, column, item)

    def _load_versions(self):
        self._versions = self.case_manager.list_graph_versions(limit=200)
        self.versions_table.setRowCount(len(self._versions))
        for row, version in enumerate(self._versions):
            values = [
                str(version.get("id") or ""),
                (version.get("created_at") or "").replace("T", " "),
                version.get("label") or "",
                version.get("action") or "",
                str(version.get("nodes") or 0),
                str(version.get("edges") or 0),
                str(version.get("content_hash") or "")[:12],
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, version.get("id"))
                self.versions_table.setItem(row, column, item)

    # -------------------------------------------------------------------- notes

    def _on_note_selected(self, current, _previous):
        if current is None:
            return
        note_id = current.data(Qt.ItemDataRole.UserRole)
        note = self.case_manager.get_note(note_id)
        if note is None:
            return
        self._current_note_id = note_id
        self.note_title.setText(note.get("title") or "")
        self.note_tags.setText(", ".join(note.get("tags") or []))
        self.note_body.setPlainText(note.get("body") or "")

    def _new_note(self):
        self._current_note_id = None
        self.notes_list.clearSelection()
        self.note_title.clear()
        self.note_tags.clear()
        self.note_body.clear()
        self.note_title.setFocus()

    def _save_note(self):
        title = self.note_title.text().strip() or "Untitled note"
        tags = self.note_tags.text().strip()
        body = self.note_body.toPlainText()
        if self._current_note_id:
            note = self.case_manager.update_note(
                self._current_note_id, title=title, body=body, tags=tags
            )
        else:
            note = self.case_manager.add_note(title, body, tags)
            self._current_note_id = note.get("id") if note else None
        self._load_notes()
        self._refresh_header()

    def _delete_note(self):
        if not self._current_note_id:
            return
        if (
            QMessageBox.question(
                self,
                "Delete note",
                "Delete this note? Attachments remain in the case evidence folder.",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.case_manager.delete_note(self._current_note_id)
        self._current_note_id = None
        self.note_title.clear()
        self.note_tags.clear()
        self.note_body.clear()
        self._load_notes()
        self._load_attachments()
        self._refresh_header()

    def _ensure_note(self) -> str | None:
        if self._current_note_id:
            return self._current_note_id
        note = self.case_manager.add_note(
            self.note_title.text().strip() or "Untitled note",
            self.note_body.toPlainText(),
            self.note_tags.text().strip(),
        )
        self._current_note_id = note.get("id") if note else None
        self._load_notes()
        return self._current_note_id

    def _attach_to_note(self):
        note_id = self._ensure_note()
        if not note_id:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Attach evidence")
        if not path:
            return
        self.case_manager.attach_file(path, note_id=note_id)
        self._load_attachments()
        self._refresh_header()

    def _capture_note_screenshot(self):
        note_id = self._ensure_note()
        attachment = self.case_manager.capture_screenshot(
            caption=self.note_title.text().strip(), note_id=note_id
        )
        if attachment is None:
            QMessageBox.warning(
                self,
                "Screenshot",
                "Could not capture the graph canvas. Open a case with a graph first.",
            )
            return
        self._load_attachments()
        self._refresh_header()

    # ---------------------------------------------------------------- evidence

    def _selected_attachment(self) -> dict | None:
        row = self.evidence_table.currentRow()
        if row < 0 or row >= len(self._attachments):
            return None
        return self._attachments[row]

    def _add_attachment(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Add evidence files")
        for path in paths:
            self.case_manager.attach_file(path)
        if paths:
            self._load_attachments()
            self._refresh_header()

    def _open_attachment(self, *_args):
        attachment = self._selected_attachment()
        if not attachment:
            return
        path = attachment.get("path") or ""
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _delete_attachment(self):
        attachment = self._selected_attachment()
        if not attachment:
            return
        if (
            QMessageBox.question(
                self, "Delete evidence", "Delete this evidence record and its file?"
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.case_manager.case_store.delete_attachment(
            attachment["id"], delete_file=True
        )
        self._load_attachments()
        self._refresh_header()

    # ----------------------------------------------------------------- requests

    def _selected_request(self) -> dict | None:
        row = self.requests_table.currentRow()
        if row < 0 or row >= len(self._requests):
            return None
        return self._requests[row]

    def _show_request_details(self):
        request = self._selected_request()
        if request is None:
            self.request_details.clear()
            return
        lines = [
            f"id: {request.get('id')}",
            f"created_at: {request.get('created_at')}",
            f"module: {request.get('module')}",
            f"target: {request.get('target')}",
            f"method: {request.get('method')}",
            f"url: {request.get('url')}",
            f"status_code: {request.get('status_code')}",
            f"duration_ms: {request.get('duration_ms')}",
            f"raw_log: {request.get('raw_path')}",
            "",
            "=== request headers ===",
            request.get("request_headers") or "",
            "",
            "=== request body ===",
            request.get("request_body") or "",
            "",
            "=== response headers ===",
            request.get("response_headers") or "",
            "",
            "=== response body ===",
            request.get("response_body") or "",
        ]
        if request.get("error"):
            lines.extend(["", "=== error ===", request["error"]])
        self.request_details.setPlainText("\n".join(lines))

    def _open_raw_log(self):
        request = self._selected_request()
        if request is None:
            return
        path = request.get("raw_path") or ""
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    # ------------------------------------------------------------------ versions

    def _selected_version(self) -> dict | None:
        row = self.versions_table.currentRow()
        if row < 0 or row >= len(self._versions):
            return None
        return self._versions[row]

    def _show_version_preview(self):
        version = self._selected_version()
        if version is None:
            self.version_preview.clear()
            return
        full = self.case_manager.get_graph_version(int(version["id"]))
        if full is None:
            self.version_preview.clear()
            return
        snapshot = full.get("snapshot") or {}
        nodes = snapshot.get("nodes") or []
        edges = snapshot.get("edges") or []
        lines = [
            f"Version {full.get('id')} · {full.get('created_at')}",
            f"Label: {full.get('label') or '(none)'}",
            f"Action: {full.get('action')}",
            f"Nodes: {len(nodes)} · Edges: {len(edges)}",
            f"Content hash: {full.get('content_hash')}",
            f"Snapshot hash: {full.get('snapshot_hash')}",
            "",
            "Nodes:",
        ]
        for node in nodes[:80]:
            lines.append(
                f"  · {node.get('entity_type', 'Custom')}: "
                f"{node.get('title', '')} [{str(node.get('id', ''))[:10]}]"
            )
        if len(nodes) > 80:
            lines.append(f"  … {len(nodes) - 80} more")
        if edges:
            lines.append("")
            lines.append("Edges:")
            for edge in edges[:40]:
                lines.append(
                    f"  · {str(edge.get('source', ''))[:8]} → "
                    f"{str(edge.get('target', ''))[:8]} "
                    f"{edge.get('relationship_type') or edge.get('label') or ''}"
                )
            if len(edges) > 40:
                lines.append(f"  … {len(edges) - 40} more")
        self.version_preview.setPlainText("\n".join(lines))

    def _save_version(self):
        label, ok = QInputDialog.getText(
            self,
            "Save graph version",
            "Version label:",
            text=f"Manual snapshot {datetime.now():%Y-%m-%d %H:%M}",
        )
        if not ok:
            return
        version = self.case_manager.save_graph_version(
            label=label.strip(), action="manual"
        )
        if version is None:
            QMessageBox.warning(
                self, "Graph history", "There is no graph canvas to snapshot."
            )
            return
        self._load_versions()
        self._refresh_header()

    def _restore_version(self):
        version = self._selected_version()
        if version is None:
            return
        if (
            QMessageBox.question(
                self,
                "Restore graph version",
                f"Replace the current graph with version {version['id']}?\n"
                "The current graph is kept in the undo stack.",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        restored = self.case_manager.restore_graph_version(int(version["id"]))
        if restored is None:
            QMessageBox.warning(self, "Graph history", "Could not restore version.")
            return
        self.graph_restored.emit()
        self._load_versions()
        self._refresh_header()

    def _delete_version(self):
        version = self._selected_version()
        if version is None:
            return
        if (
            QMessageBox.question(
                self, "Delete version", f"Delete graph version {version['id']}?"
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.case_manager.delete_graph_version(int(version["id"]))
        self._load_versions()
        self._refresh_header()

    # ------------------------------------------------------------------- theme

    def _apply_theme(self):
        pal = dialog_palette()
        self.setStyleSheet(
            f"""
            QDialog {{ background-color: {pal["bg"]}; color: {pal["text"]}; }}
            QLabel {{ color: {pal["text"]}; }}
            QTabWidget::pane {{
                border: 1px solid {pal["border"]};
                border-radius: {pal["radius"]};
                background-color: {pal["surface"]};
            }}
            QTabBar::tab {{
                background-color: {pal["bg"]};
                color: {pal["text_muted"]};
                border: 1px solid {pal["border"]};
                border-bottom: none;
                padding: 7px 14px;
            }}
            QTabBar::tab:selected {{
                color: {pal["text"]};
                background-color: {pal["surface"]};
            }}
            QLineEdit, QPlainTextEdit, QListWidget, QTableWidget {{
                background-color: {pal["surface"]};
                color: {pal["text"]};
                border: 1px solid {pal["border"]};
                border-radius: {pal["radius_sm"]};
                padding: 4px;
            }}
            QListWidget::item:selected, QTableWidget::item:selected {{
                background-color: {pal["surface_hover"]};
                color: {pal["text"]};
            }}
            QHeaderView::section {{
                background-color: {pal["surface"]};
                color: {pal["text"]};
                border: none;
                border-bottom: 1px solid {pal["border"]};
                padding: 5px;
            }}
            QPushButton {{
                background-color: {pal["surface"]};
                color: {pal["text"]};
                border: 1px solid {pal["border"]};
                border-radius: {pal["radius"]};
                padding: 6px 14px;
                min-height: 24px;
            }}
            QPushButton:hover {{
                border-color: {pal["border_hover"]};
                background-color: {pal["surface_hover"]};
            }}
            """
        )


__all__ = ["CaseDialog"]
