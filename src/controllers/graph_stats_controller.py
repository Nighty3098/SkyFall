from collections import Counter

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtWidgets import QListWidget, QListWidgetItem

from src.libs.graph_lib import (
    ENTITY_COLORS,
    ENTITY_SYMBOLS,
    EdgeItem,
    NodeItem,
)
from src.libs.graph_panel import _swatch
from src.ui.theme import dialog_palette


class GraphStatsController:
    """Fill the native statistics widgets declared in ``form.ui``.

    The panel itself is plain Qt Designer markup (labels and two
    ``QListWidget``s); this controller only computes the counts and writes
    them into those widgets whenever the graph changes.
    """

    REFRESH_DELAY_MS = 120

    def __init__(self, ui, graph_widget):
        self.ui = ui
        self.graph = graph_widget
        self._stats: dict = {}

        self._timer = QTimer(ui)
        self._timer.setSingleShot(True)
        self._timer.setInterval(self.REFRESH_DELAY_MS)
        self._timer.timeout.connect(self.refresh)

        graph_widget._scene.changed.connect(self._schedule_refresh)
        graph_widget.selectionChanged.connect(self._schedule_refresh)
        self.refresh()

    def stats(self) -> dict:
        """Return the last computed statistics."""
        return {
            **self._stats,
            "entity_types": dict(self._stats.get("entity_types", {})),
            "relationship_types": dict(self._stats.get("relationship_types", {})),
        }

    def _schedule_refresh(self, *_args):
        self._timer.start()

    def refresh(self) -> dict:
        self._timer.stop()
        try:
            items = self.graph._scene.items()
        except RuntimeError:
            items = []

        nodes = [item for item in items if isinstance(item, NodeItem)]
        edges = [item for item in items if isinstance(item, EdgeItem)]

        entity_counts = Counter(node.entity_type or "Custom" for node in nodes)
        relationship_counts = Counter(
            edge.relationship_type or "associated_with" for edge in edges
        )

        self._stats = {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "evidence": sum(len(node.evidence or []) for node in nodes),
            "visible_nodes": sum(1 for node in nodes if node.isVisible()),
            "selected_nodes": sum(1 for node in nodes if node.isSelected()),
            "isolated_nodes": sum(1 for node in nodes if not node._connected_edges()),
            "entity_types": dict(entity_counts),
            "relationship_types": dict(relationship_counts),
        }
        self._render()
        return self.stats()

    def _render(self):
        stats = self._stats
        nodes = stats.get("total_nodes", 0)
        edges = stats.get("total_edges", 0)

        self.ui.graphStatsSummary.setText(
            f"{nodes} nodes \u00b7 {edges} edges \u00b7 "
            f"{stats.get('evidence', 0)} evidence"
        )
        self.ui.graphStatsMeta.setText(
            f"{stats.get('visible_nodes', 0)} of {nodes} visible \u00b7 "
            f"{stats.get('selected_nodes', 0)} selected \u00b7 "
            f"{stats.get('isolated_nodes', 0)} isolated"
        )

        palette = dialog_palette()
        self._fill_list(
            self.ui.graphStatsEntityList,
            stats.get("entity_types", {}),
            nodes,
            symbol_fn=lambda name: ENTITY_SYMBOLS.get(name, ""),
            color_fn=lambda name: ENTITY_COLORS.get(name, palette["text_muted"]),
            humanize=lambda name: name,
            empty_text="No entities yet",
        )
        self._fill_list(
            self.ui.graphStatsRelationshipList,
            stats.get("relationship_types", {}),
            edges,
            symbol_fn=lambda _name: "\u2194",
            color_fn=lambda _name: palette["accent"],
            humanize=lambda name: name.replace("_", " "),
            empty_text="No relationships yet",
        )

    def _fill_list(
        self,
        widget: QListWidget,
        counts: dict,
        total: int,
        *,
        symbol_fn,
        color_fn,
        humanize,
        empty_text: str,
    ):
        widget.clear()

        if not counts:
            item = QListWidgetItem(empty_text)
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            widget.addItem(item)
            return

        ordered = sorted(
            counts.items(), key=lambda entry: (-entry[1], entry[0].lower())
        )
        for name, count in ordered:
            share = (count / total * 100.0) if total else 0.0
            label = humanize(name)
            item = QListWidgetItem(
                f"  {symbol_fn(name)}  {label} \u2014 {count} ({share:.0f}%)"
            )
            item.setData(Qt.ItemDataRole.DecorationRole, _swatch(color_fn(name), 12))
            item.setSizeHint(QSize(0, 24))
            item.setToolTip(f"{label}: {count} ({share:.0f}%)")
            widget.addItem(item)
