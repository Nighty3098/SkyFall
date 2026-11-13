"""Menu actions and lifecycle for the unified case workspace.

The case database and the graph widget are independent: the manager knows how
to snapshot the graph, while the widget knows when its content changed.  This
controller is the small glue layer that exposes both through menu actions and
automatically records graph versions after edits.
"""

from __future__ import annotations

from loguru import logger
from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QInputDialog, QMessageBox

from src.ui.case_dialog import CaseDialog

CASE_MANAGER_TAB = 0
GRAPH_HISTORY_TAB = 3


class CaseController:
    """Own the case dialog and the graph-version autosave timer."""

    AUTO_VERSION_DELAY_MS = 1800

    def __init__(self, ui, case_manager, graph_widget=None):
        self.ui = ui
        self.case_manager = case_manager
        self.graph = graph_widget
        self._dialog: CaseDialog | None = None
        self._last_action = "graph_changed"

        self._version_timer = QTimer(ui)
        self._version_timer.setSingleShot(True)
        self._version_timer.setInterval(self.AUTO_VERSION_DELAY_MS)
        self._version_timer.timeout.connect(self._auto_save_version)

        if self.graph is not None:
            self.graph.graphChanged.connect(self._on_graph_changed)

        self._build_actions()

    # ------------------------------------------------------------------ actions

    def _build_actions(self):
        parent = self.ui
        self.action_case_manager = QAction("Case Manager\u2026", parent)
        self.action_case_manager.setShortcut(QKeySequence("Ctrl+Alt+C"))
        self.action_case_manager.triggered.connect(
            lambda checked=False: self.open_case_manager(CASE_MANAGER_TAB)
        )

        self.action_graph_history = QAction("Graph History\u2026", parent)
        self.action_graph_history.setShortcut(QKeySequence("Ctrl+Alt+H"))
        self.action_graph_history.triggered.connect(
            lambda checked=False: self.open_case_manager(GRAPH_HISTORY_TAB)
        )

        self.action_save_version = QAction("Save Graph Version\u2026", parent)
        self.action_save_version.setShortcut(QKeySequence("Ctrl+Alt+S"))
        self.action_save_version.triggered.connect(self.save_graph_version)

        self.action_find_duplicates = QAction("Find Duplicate Entities\u2026", parent)
        self.action_find_duplicates.triggered.connect(self.find_duplicates)
        self.action_merge_selected = QAction("Merge Selected Entities", parent)
        self.action_merge_selected.triggered.connect(self.merge_selected)
        self.action_auto_resolve = QAction("Auto-resolve after Transforms", parent)
        self.action_auto_resolve.setCheckable(True)
        self.action_auto_resolve.setChecked(
            bool(getattr(self.graph, "_auto_resolve_enabled", True))
        )
        self.action_auto_resolve.toggled.connect(self.set_auto_resolve)

        file_menu = getattr(self.ui, "menuFile", None)
        if file_menu is not None:
            file_menu.addSeparator()
            for action in (
                self.action_case_manager,
                self.action_save_version,
                self.action_graph_history,
            ):
                file_menu.addAction(action)

        graph_menu = getattr(self.ui, "menuGraph", None)
        if graph_menu is not None:
            graph_menu.addSeparator()
            for action in (
                self.action_find_duplicates,
                self.action_merge_selected,
                self.action_auto_resolve,
            ):
                graph_menu.addAction(action)

        self._update_actions()

    def _update_actions(self):
        has_graph = self.graph is not None
        has_nodes = False
        if has_graph:
            try:
                has_nodes = self.graph._has_nodes()
            except (AttributeError, RuntimeError):
                has_nodes = False
        self.action_save_version.setEnabled(has_nodes)
        self.action_find_duplicates.setEnabled(has_nodes)
        self.action_merge_selected.setEnabled(has_nodes)

    def set_auto_resolve(self, enabled: bool):
        if self.graph is not None:
            self.graph.set_auto_resolve_enabled(bool(enabled))

    def find_duplicates(self):
        if self.graph is None:
            return
        self.graph.run_entity_resolution(False)

    def merge_selected(self):
        if self.graph is None:
            return
        self.graph.merge_selected_entities()

    # -------------------------------------------------------------- graph history

    def save_graph_version(self):
        if self.graph is None:
            return
        label, ok = QInputDialog.getText(
            self.ui,
            "Save graph version",
            "Version label:",
        )
        if not ok:
            return
        try:
            version = self.case_manager.save_graph_version(
                label=label.strip(), action="manual"
            )
        except Exception as exc:  # pragma: no cover - surfaced in the UI
            logger.exception("Failed to save graph version")
            QMessageBox.warning(
                self.ui, "Graph history", f"Could not save the graph version:\n{exc}"
            )
            return
        if version is None:
            QMessageBox.warning(
                self.ui, "Graph history", "There is no graph canvas to snapshot."
            )
            return
        if version.get("created", True):
            self.graph.status_message(f"Graph version {version.get('id')} saved")
        else:
            self.graph.status_message("Graph unchanged since the latest version")

    def _on_graph_changed(self, action: str):
        self._last_action = str(action or "graph_changed")
        self._update_actions()
        if self.case_manager.current_case_path is None:
            return
        self._version_timer.start()

    def _auto_save_version(self):
        if self.graph is None or self.case_manager.current_case_path is None:
            return
        try:
            snapshot = self.graph.to_dict()
            if not snapshot.get("nodes"):
                return
            self.case_manager.save_graph_version(
                snapshot,
                label=f"Auto: {self._last_action.replace('_', ' ')}",
                action=self._last_action,
            )
        except Exception:  # pragma: no cover - storage errors must not break edits
            logger.exception("Failed to record the automatic graph version")

    # --------------------------------------------------------------- case dialog

    def open_case_manager(self, tab: int = CASE_MANAGER_TAB):
        if self._dialog is None:
            self._dialog = CaseDialog(self.case_manager, self.ui)
            self._dialog.graph_restored.connect(self._on_graph_restored)
        else:
            self._dialog.refresh_all()
        self._dialog.tabs.setCurrentIndex(tab)
        self._dialog.show()
        self._dialog.raise_()
        self._dialog.activateWindow()

    def _on_graph_restored(self):
        if self.graph is not None:
            try:
                self.graph.viewport().update()
            except RuntimeError:
                pass
        self._update_actions()

    def shutdown(self):
        if self._version_timer.isActive():
            self._version_timer.stop()
            self._auto_save_version()
        if self._dialog is not None:
            self._dialog.close()
            self._dialog = None


__all__ = ["CaseController"]
