import json
import sys

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QTextOption,
)
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGraphicsDropShadowEffect,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsView,
    QLineEdit,
    QMenu,
    QPlainTextEdit,
    QVBoxLayout,
)

PORT_DIR = {
    "left": (-1, 0),
    "right": (1, 0),
    "top": (0, -1),
    "bottom": (0, 1),
}

INPUT_PORTS = {"left", "top"}
OUTPUT_PORTS = {"right", "bottom"}


def _theme_colors():
    palette = QApplication.palette()
    bg = palette.color(QPalette.ColorRole.Window)
    dark = bg.lightness() < 128
    return {
        "card_bg_start": QColor("#2a2a3e") if dark else QColor("#f0f4fc"),
        "card_bg_end": QColor("#1a1a2e") if dark else QColor("#d9e2f0"),
        "card_border": QColor("#5555aa") if dark else QColor("#3b5998"),
        "card_title": QColor("#e0e0f0") if dark else QColor("#1a1a2e"),
        "card_content": QColor("#a0a0c0") if dark else QColor("#333355"),
        "port_input": QColor("#ff6b6b"),
        "port_output": QColor("#4ecdc4"),
        "edge_color": QColor("#8888cc") if dark else QColor("#2c3e50"),
    }


class NodeItem(QGraphicsItem):
    def __init__(self, title="Node", content="", node_id=None, parent=None):
        super().__init__(parent)
        self.id = node_id if node_id is not None else id(self)
        self.title = title
        self.content = content
        self._width = 160
        self._height = 90
        self._port_radius = 6
        self._dragging_edge = False
        self._drag_port = None
        self._temp_edge = None

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setOffset(3, 3)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)

    def boundingRect(self):
        m = self._port_radius + 2
        return QRectF(-m, -m, self._width + 2*m, self._height + 2*m)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = _theme_colors()

        rect = QRectF(0, 0, self._width, self._height).adjusted(1, 1, -1, -1)
        gradient = QLinearGradient(0, 0, 0, self._height)
        gradient.setColorAt(0, c["card_bg_start"])
        gradient.setColorAt(1, c["card_bg_end"])
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(c["card_border"], 2))
        painter.drawRoundedRect(rect, 10, 10)

        painter.setPen(c["card_title"])
        font_title = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(font_title)
        title_rect = QRectF(10, 8, self._width - 20, 20)
        painter.drawText(
            title_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.title,
        )

        if self.content:
            painter.setPen(c["card_content"])
            font_content = QFont("Segoe UI", 8)
            painter.setFont(font_content)
            content_rect = QRectF(10, 32, self._width - 20, self._height - 40)
            opt = QTextOption()
            opt.setWrapMode(QTextOption.WrapMode.WordWrap)
            painter.drawText(content_rect, self.content, opt)

        painter.setPen(Qt.PenStyle.NoPen)
        for name, pos in self._ports().items():
            painter.setBrush(QBrush(c["port_input"] if name in INPUT_PORTS else c["port_output"]))
            painter.drawEllipse(pos, self._port_radius, self._port_radius)

    def _ports(self):
        return {
            "left": QPointF(0, self._height / 2),
            "right": QPointF(self._width, self._height / 2),
            "top": QPointF(self._width / 2, 0),
            "bottom": QPointF(self._width / 2, self._height),
        }

    def port_pos(self, name):
        return self._ports()[name]

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self._connected_edges():
                edge.adjust()
        return super().itemChange(change, value)

    def _connected_edges(self):
        edges = []
        if self.scene():
            for item in self.scene().items():
                if isinstance(item, EdgeItem) and (
                    item.source == self or item.target == self
                ):
                    edges.append(item)
        return edges

    def _port_at_pos(self, pos):
        r = self._port_radius + 4
        for name, p in self._ports().items():
            if (pos - p).manhattanLength() < r:
                return name
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            port = self._port_at_pos(event.pos())
            if port:
                self._drag_port = port
                self._start_edge_drag(event)
                return
        super().mousePressEvent(event)

    def _start_edge_drag(self, event):
        self._temp_edge = QGraphicsPathItem()
        pen = QPen(QColor("#2c3e50"), 2, Qt.PenStyle.DashLine)
        self._temp_edge.setPen(pen)
        self.scene().addItem(self._temp_edge)
        self._dragging_edge = True

    def mouseMoveEvent(self, event):
        if self._dragging_edge and self._temp_edge:
            start = self.mapToScene(self.port_pos(self._drag_port))
            end = event.scenePos()
            dx, dy = PORT_DIR[self._drag_port]
            path = QPainterPath()
            path.moveTo(start)
            offset = max(abs(end.x() - start.x()) * 0.4, abs(end.y() - start.y()) * 0.4, 30)
            ctrl1 = QPointF(start.x() + dx * offset, start.y() + dy * offset)
            ctrl2 = QPointF(end.x(), end.y())
            path.cubicTo(ctrl1, ctrl2, end)
            self._temp_edge.setPath(path)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragging_edge:
            self._dragging_edge = False
            if self._temp_edge:
                self.scene().removeItem(self._temp_edge)
                self._temp_edge = None

            target_node = None
            for item in self.scene().items(event.scenePos()):
                if isinstance(item, NodeItem) and item != self:
                    target_node = item
                    break

            if target_node:
                for view in self.scene().views():
                    if isinstance(view, GraphWidget):
                        source, source_port = (self, self._drag_port)
                        target, _ = (target_node, None)
                        if self._drag_port in INPUT_PORTS:
                            source, target = target, self
                            source_port = target._port_at_pos(target.mapFromScene(event.scenePos())) or "left"
                        view.add_edge(source, target, source_port)
                        break
            self._drag_port = None
        else:
            super().mouseReleaseEvent(event)

class EdgeItem(QGraphicsPathItem):
    def __init__(self, source: NodeItem, target: NodeItem, source_port="right", target_port="left", parent=None):
        super().__init__(parent)
        self.source = source
        self.target = target
        self.source_port = source_port
        self.target_port = target_port
        self.setPen(QPen(_theme_colors()["edge_color"], 2.5))
        self.setZValue(-1)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.adjust()

    def adjust(self):
        src = self.source.mapToScene(self.source.port_pos(self.source_port))
        tgt = self.target.mapToScene(self.target.port_pos(self.target_port))
        path = QPainterPath()
        path.moveTo(src)

        sdx, sdy = PORT_DIR[self.source_port]
        tdx, tdy = PORT_DIR[self.target_port]
        dist = (tgt - src).manhattanLength()
        offset = max(dist * 0.4, 30)

        ctrl1 = QPointF(src.x() + sdx * offset, src.y() + sdy * offset)
        ctrl2 = QPointF(tgt.x() + tdx * offset, tgt.y() + tdy * offset)
        path.cubicTo(ctrl1, ctrl2, tgt)

        self.setPath(path)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = _theme_colors()
        pen = QPen(
            c["edge_color"],
            2.5,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self.path())

        if self.path().elementCount() > 0:
            last_pt = self.path().currentPosition()
            path_length = self.path().length()
            if path_length > 10:
                percent = 1.0 - 10 / path_length
                prev_pt = self.path().pointAtPercent(percent)
            else:
                prev_pt = self.path().pointAtPercent(0)

            line = QLineF(prev_pt, last_pt)
            angle = -line.angle()

            painter.save()
            painter.translate(last_pt)
            painter.rotate(angle)
            arrow_size = 12
            painter.setBrush(QBrush(c["edge_color"]))
            painter.setPen(Qt.PenStyle.NoPen)
            arrow_path = QPainterPath()
            arrow_path.moveTo(0, 0)
            arrow_path.lineTo(-arrow_size, -arrow_size / 2)
            arrow_path.lineTo(-arrow_size, arrow_size / 2)
            arrow_path.closeSubpath()
            painter.drawPath(arrow_path)
            painter.restore()

class NodeEditDialog(QDialog):
    def __init__(self, title="", content="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Node")
        self.setModal(True)
        self.resize(400, 300)

        layout = QVBoxLayout(self)

        form_layout = QFormLayout()
        self.title_edit = QLineEdit(title)
        self.title_edit.setMinimumWidth(250)
        form_layout.addRow("Title:", self.title_edit)

        self.content_edit = QPlainTextEdit(content)
        self.content_edit.setMinimumHeight(120)
        form_layout.addRow("Content:", self.content_edit)

        layout.addLayout(form_layout)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_data(self):
        return self.title_edit.text(), self.content_edit.toPlainText()

class GraphWidget(QGraphicsView):
    nodeAdded = Signal(dict)
    edgeAdded = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)

        self._scene = QGraphicsScene(self)
        self._scene.setSceneRect(-5000, -5000, 10000, 10000)
        self.setScene(self._scene)

        self.graph_data = {"nodes": [], "edges": []}

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, pos):
        scene_pos = self.mapToScene(pos)
        item = self._scene.itemAt(scene_pos, self.transform())
        menu = QMenu(self)

        if isinstance(item, EdgeItem):
            delete_action = QAction("Delete Edge", self)
            delete_action.triggered.connect(lambda: self.remove_edge(item))
            menu.addAction(delete_action)
        elif isinstance(item, NodeItem):
            edit_action = QAction("Edit", self)
            edit_action.triggered.connect(lambda: self.edit_node(item))
            menu.addAction(edit_action)
            menu.addSeparator()
            delete_action = QAction("Delete Node", self)
            delete_action.triggered.connect(lambda: self.remove_node(item))
            menu.addAction(delete_action)
        else:
            add_action = QAction("Add Node", self)
            add_action.triggered.connect(lambda: self.add_node(scene_pos))
            menu.addAction(add_action)

        menu.exec(self.viewport().mapToGlobal(pos))

    def edit_node(self, node: NodeItem):
        dialog = NodeEditDialog(node.title, node.content, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_title, new_content = dialog.get_data()
            node.title = new_title
            node.content = new_content
            node.update()
            for n_data in self.graph_data["nodes"]:
                if n_data["id"] == node.id:
                    n_data["title"] = new_title
                    n_data["content"] = new_content
                    break

    def add_node(self, scene_pos):
        node = NodeItem(title="New node")
        node.setPos(scene_pos)
        self._scene.addItem(node)
        node_data = {
            "id": node.id,
            "title": node.title,
            "content": node.content,
            "x": scene_pos.x(),
            "y": scene_pos.y(),
        }
        self.graph_data["nodes"].append(node_data)
        self.nodeAdded.emit(node_data)
        return node

    def add_edge(self, source_node, target_node, source_port="right", target_port=None):
        if target_port is None:
            target_port = "left" if source_port in OUTPUT_PORTS else "right"
        edge = EdgeItem(source_node, target_node, source_port, target_port)
        self._scene.addItem(edge)
        edge_data = {
            "source": source_node.id,
            "target": target_node.id,
            "source_port": source_port,
            "target_port": target_port,
        }
        self.graph_data["edges"].append(edge_data)
        self.edgeAdded.emit(edge_data)
        return edge

    def remove_node(self, node: NodeItem):
        for edge in node._connected_edges():
            self.remove_edge(edge, remove_from_data=True)
        self._scene.removeItem(node)
        self.graph_data["nodes"] = [
            n for n in self.graph_data["nodes"] if n["id"] != node.id
        ]

    def remove_edge(self, edge: EdgeItem, remove_from_data=True):
        self._scene.removeItem(edge)
        if remove_from_data:
            self.graph_data["edges"] = [
                e
                for e in self.graph_data["edges"]
                if not (
                    e["source"] == edge.source.id
                    and e["target"] == edge.target.id
                    and e.get("source_port") == edge.source_port
                    and e.get("target_port") == edge.target_port
                )
            ]

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            for item in self._scene.selectedItems():
                if isinstance(item, NodeItem):
                    self.remove_node(item)
                elif isinstance(item, EdgeItem):
                    self.remove_edge(item)
        else:
            super().keyPressEvent(event)

    def to_dict(self):
        nodes = []
        edges = []
        for item in self._scene.items():
            if isinstance(item, NodeItem):
                nodes.append(
                    {
                        "id": item.id,
                        "title": item.title,
                        "content": item.content,
                        "x": item.pos().x(),
                        "y": item.pos().y(),
                    }
                )
            elif isinstance(item, EdgeItem):
                edges.append({
                    "source": item.source.id,
                    "target": item.target.id,
                    "source_port": item.source_port,
                    "target_port": item.target_port,
                })
        return {"nodes": nodes, "edges": edges}

    def from_dict(self, data):
        self._scene.clear()
        self.graph_data = {"nodes": [], "edges": []}
        node_map = {}
        for n in data["nodes"]:
            node = NodeItem(
                title=n.get("title", "Node"),
                content=n.get("content", ""),
                node_id=n["id"],
            )
            node.setPos(n["x"], n["y"])
            self._scene.addItem(node)
            node_map[n["id"]] = node
            self.graph_data["nodes"].append(
                {
                    "id": node.id,
                    "title": node.title,
                    "content": node.content,
                    "x": node.pos().x(),
                    "y": node.pos().y(),
                }
            )
        for e in data["edges"]:
            src = node_map.get(e["source"])
            tgt = node_map.get(e["target"])
            if src and tgt:
                sp = e.get("source_port", "right")
                tp = e.get("target_port", "left")
                edge = EdgeItem(src, tgt, sp, tp)
                self._scene.addItem(edge)
                self.graph_data["edges"].append({"source": src.id, "target": tgt.id, "source_port": sp, "target_port": tp})

    def save_to_json(self, filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    def load_from_json(self, filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.from_dict(data)

if __name__ == "__main__":
    import os

    SAVE_FILE = "graph.json"

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = GraphWidget()
    window.setWindowTitle("Interactive Graph – JSON Persistence")
    window.resize(900, 650)

    if os.path.exists(SAVE_FILE):
        try:
            window.load_from_json(SAVE_FILE)
        except Exception as e:
            print(f"Error loading graph: {e}")
    else:
        n1 = window.add_node(QPointF(-200, -80))
        n1.title = "Start"
        n1.content = "Beginning of the process"
        n1.update()

        n2 = window.add_node(QPointF(150, 80))
        n2.title = "Finish"
        n2.content = "Final goal"
        n2.update()

        n3 = window.add_node(QPointF(150, -200))
        n3.title = "Intermediate"
        n3.content = "An additional step"
        n3.update()

        window.add_edge(n1, n2)
        window.add_edge(n3, n1)

    def save_on_exit():
        window.save_to_json(SAVE_FILE)

    app.aboutToQuit.connect(save_on_exit)

    window.show()
    sys.exit(app.exec())
