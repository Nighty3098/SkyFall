from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QGuiApplication

from src.libs.graph_lib import EdgeItem, NodeItem
from src.modules.graph_layout import LAYOUT_ALGORITHMS, compute_layout


class GraphLayoutController:
    def __init__(self, ui, graph_widget):
        self.ui = ui
        self.graph_widget = graph_widget

    def apply_layout(self, algorithm: str = "spring"):
        gw = self.graph_widget
        nodes = []
        edges = []
        node_items = {}

        for item in gw._scene.items():
            if isinstance(item, NodeItem):
                node_items[item.id] = item
                nodes.append(
                    {
                        "id": item.id,
                        "title": item.title,
                        "entity_type": item.entity_type,
                        "content": item.content,
                        "x": item.pos().x(),
                        "y": item.pos().y(),
                    }
                )
            elif isinstance(item, EdgeItem):
                edges.append(
                    {
                        "source": item.source.id,
                        "target": item.target.id,
                        "label": item.label,
                        "relationship_type": item.relationship_type,
                    }
                )

        if not nodes:
            gw.status_message("Nothing to lay out \u2014 the graph is empty")
            return

        selected_ids = {item.id for item in node_items.values() if item.isSelected()}
        selected_only = bool(selected_ids)
        if selected_only:
            nodes = [node for node in nodes if node["id"] in selected_ids]
            edges = [
                edge
                for edge in edges
                if edge["source"] in selected_ids and edge["target"] in selected_ids
            ]

        label = LAYOUT_ALGORITHMS.get(algorithm, algorithm)
        scope = "selected nodes" if selected_only else "all nodes"
        gw.status_message(f"Applying {label} layout to {scope}\u2026")
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = compute_layout(nodes, edges, algorithm=algorithm)
        finally:
            QGuiApplication.restoreOverrideCursor()

        if selected_only:
            center_x = sum(
                node_items[node_id].pos().x() + node_items[node_id]._width / 2.0
                for node_id in selected_ids
            ) / len(selected_ids)
            center_y = sum(
                node_items[node_id].pos().y() + node_items[node_id]._height / 2.0
                for node_id in selected_ids
            ) / len(selected_ids)
            result_x = sum(x for x, _ in result.positions.values()) / len(
                result.positions
            )
            result_y = sum(y for _, y in result.positions.values()) / len(
                result.positions
            )
            offset_x = center_x - result_x
            offset_y = center_y - result_y
        else:
            offset_x = offset_y = 0.0

        gw.push_undo_state()
        for node_id, (x, y) in result.positions.items():
            node = node_items.get(node_id)
            if node:
                # Layout coordinates are node centres; graph items use top-left.
                node.setPos(
                    QPointF(
                        x + offset_x - node._width / 2.0,
                        y + offset_y - node._height / 2.0,
                    )
                )

        gw.viewport().update()
        if not selected_only:
            gw.fit_to_view()
        gw.status_message(f"Applied {label} layout to {len(result.positions)} {scope}")
