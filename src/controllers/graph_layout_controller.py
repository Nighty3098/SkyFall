from PySide6.QtCore import QPointF

from src.libs.graph_lib import EdgeItem, NodeItem
from src.modules.graph_layout import compute_layout


class GraphLayoutController:
    def __init__(self, ui, graph_widget):
        self.ui = ui
        self.graph_widget = graph_widget

    def apply_layout(self, algorithm: str = "spring"):
        gw = self.graph_widget
        nodes = []
        edges = []

        for item in gw._scene.items():
            if isinstance(item, NodeItem):
                nodes.append(
                    {
                        "id": item.id,
                        "title": item.title,
                        "x": item.pos().x(),
                        "y": item.pos().y(),
                    }
                )
            elif isinstance(item, EdgeItem):
                edges.append(
                    {
                        "source": item.source.id,
                        "target": item.target.id,
                    }
                )

        if not nodes:
            return

        result = compute_layout(nodes, edges, algorithm=algorithm)

        node_map = {}
        for item in gw._scene.items():
            if isinstance(item, NodeItem):
                node_map[item.id] = item

        for node_id, (x, y) in result.positions.items():
            node = node_map.get(node_id)
            if node:
                # Layout coordinates are node centres; graph items use top-left.
                node.setPos(QPointF(x - node._width / 2.0, y - node._height / 2.0))

        gw.viewport().update()
