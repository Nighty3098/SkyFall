"""Graph menu actions for entity resolution.

The graph widget already exposes duplicate detection and merging through its
context menu; this controller mirrors them in the application's **Graph** menu
so they are discoverable without right-clicking.
"""

from __future__ import annotations

from PySide6.QtGui import QAction


class GraphEntityController:
    """Expose duplicate detection and entity merging through the Graph menu."""

    def __init__(self, ui, graph_widget=None):
        self.ui = ui
        self.graph = graph_widget

        if self.graph is not None:
            self.graph.graphChanged.connect(self._on_graph_changed)

        self._build_actions()

    def _build_actions(self):
        parent = self.ui
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
        has_nodes = False
        if self.graph is not None:
            try:
                has_nodes = self.graph._has_nodes()
            except (AttributeError, RuntimeError):
                has_nodes = False
        self.action_find_duplicates.setEnabled(has_nodes)
        self.action_merge_selected.setEnabled(has_nodes)

    def _on_graph_changed(self, action: str):
        self._update_actions()

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


__all__ = ["GraphEntityController"]
