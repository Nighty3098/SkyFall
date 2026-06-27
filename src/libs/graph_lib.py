import json
import sys
import uuid

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QTextOption,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QGraphicsDropShadowEffect,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

ENTITY_TYPES = [
    ("Person", "#4ecdc4"),
    ("Domain", "#45b7d1"),
    ("IP", "#f9ca24"),
    ("Email", "#6c5ce7"),
    ("Phone", "#fd79a8"),
    ("Username", "#00b894"),
    ("Crypto", "#f39c12"),
    ("Organization", "#e17055"),
    ("Custom", "#636e72"),
]

ENTITY_NAMES = [e[0] for e in ENTITY_TYPES]
ENTITY_COLORS = {e[0]: e[1] for e in ENTITY_TYPES}

PORT_DIR = {
    "left": (-1, 0),
    "right": (1, 0),
    "top": (0, -1),
    "bottom": (0, 1),
}

def _theme_colors(dark=None):
    if dark is None:
        ss = QApplication.instance().styleSheet()
        dark = "#0A0A0A" in ss
    return {
        "card_bg": QColor("#161616" if dark else "#E8E8E8"),
        "card_border": QColor("#262626" if dark else "#D0D0D0"),
        "card_title": QColor("#C1C1C1" if dark else "#3A3A3A"),
        "card_content": QColor("#888888"),
        "port_color": QColor("#C1C1C1" if dark else "#3A3A3A"),
        "edge_color": QColor("#262626" if dark else "#D0D0D0"),
    }


class NodeItem(QGraphicsItem):
    def __init__(self, title="Node", content="", entity_type="Custom", node_id=None, parent=None):
        super().__init__(parent)
        self.id = node_id if node_id is not None else uuid.uuid4().hex
        self.title = title
        self.content = content
        self.entity_type = entity_type if entity_type in ENTITY_NAMES else "Custom"
        self._width = 160
        self._height = 100
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
        return QRectF(-m, -m, self._width + 2 * m, self._height + 2 * m)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = _theme_colors()

        rect = QRectF(0, 0, self._width, self._height).adjusted(1, 1, -1, -1)
        painter.setBrush(QBrush(c["card_bg"]))
        border_width = 3 if self.isSelected() else 1.5
        painter.setPen(
            QPen(
                c["card_border"] if not self.isSelected() else c["port_color"],
                border_width,
            )
        )
        painter.drawRoundedRect(rect, 10, 10)

        type_color = QColor(ENTITY_COLORS.get(self.entity_type, "#636e72"))
        badge_rect = QRectF(10, 6, self._width - 20, 16)
        painter.setBrush(QBrush(type_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(badge_rect, 4, 4)
        painter.setPen(QColor("#ffffff"))
        font_badge = QFont("Segoe UI", 7, QFont.Weight.Bold)
        painter.setFont(font_badge)
        painter.drawText(
            badge_rect,
            Qt.AlignmentFlag.AlignCenter,
            self.entity_type.upper(),
        )

        painter.setPen(c["card_title"])
        font_title = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(font_title)
        title_rect = QRectF(10, 26, self._width - 20, 20)
        painter.drawText(
            title_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.title,
        )

        if self.content:
            painter.setPen(c["card_content"])
            font_content = QFont("Segoe UI", 8)
            painter.setFont(font_content)
            content_rect = QRectF(10, 48, self._width - 20, self._height - 56)
            opt = QTextOption()
            opt.setWrapMode(QTextOption.WrapMode.WordWrap)
            painter.drawText(content_rect, self.content, opt)

        painter.setPen(Qt.PenStyle.NoPen)
        for _, pos in self._ports().items():
            painter.setBrush(QBrush(c["port_color"]))
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

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self._port_at_pos(event.pos()):
            for view in self.scene().views():
                if isinstance(view, GraphWidget):
                    view.edit_node(self)
                    break
        super().mouseDoubleClickEvent(event)

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
            offset = max(
                abs(end.x() - start.x()) * 0.4, abs(end.y() - start.y()) * 0.4, 30
            )
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
                        tp = target_node._port_at_pos(
                            target_node.mapFromScene(event.scenePos())
                        ) or "left"
                        view.add_edge(self, target_node, self._drag_port, tp)
                        break
            self._drag_port = None
        else:
            super().mouseReleaseEvent(event)


class EdgeItem(QGraphicsPathItem):
    def __init__(
        self,
        source: NodeItem,
        target: NodeItem,
        source_port="right",
        target_port="left",
        parent=None,
    ):
        super().__init__(parent)
        self.source = source
        self.target = target
        self.source_port = source_port
        self.target_port = target_port
        self.setPen(QPen(_theme_colors()["edge_color"], 4))
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
            4,
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
    def __init__(self, title="", content="", entity_type="Custom", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Node")
        self.setModal(True)
        self.resize(400, 300)

        ss = QApplication.instance().styleSheet()
        dark = "#0A0A0A" in ss
        bg = "#0A0A0A" if dark else "#F5F5F5"
        surface = "#161616" if dark else "#E8E8E8"
        border = "#262626" if dark else "#D0D0D0"
        text = "#C1C1C1" if dark else "#3A3A3A"

        self.setStyleSheet(f"""
            NodeEditDialog {{
                background-color: {bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            NodeEditDialog QLineEdit, NodeEditDialog QPlainTextEdit {{
                border-radius: 10px;
                border: 1px solid {border};
                background-color: {surface};
                color: {text};
                padding: 5px;
                selection-background-color: {text};
                selection-color: {bg};
            }}
            NodeEditDialog QLineEdit:focus, NodeEditDialog QPlainTextEdit:focus {{
                border: 1px solid {text};
            }}
            NodeEditDialog QLineEdit::placeholder, NodeEditDialog QPlainTextEdit::placeholder {{
                color: {border};
            }}
            NodeEditDialog QPushButton {{
                border-radius: 10px;
                border: 1px solid {border};
                background-color: {surface};
                color: {text};
                padding: 6px 16px;
                min-height: 24px;
            }}
            NodeEditDialog QPushButton:hover {{
                background-color: {border};
                color: {text};
            }}
            NodeEditDialog QPushButton:pressed {{
                background-color: {text};
                color: {bg};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self.title_edit = QLineEdit(title)
        self.title_edit.setPlaceholderText("Title")
        layout.addWidget(self.title_edit)

        self.content_edit = QPlainTextEdit(content)
        self.content_edit.setPlaceholderText("Content")
        self.content_edit.setMinimumHeight(120)
        layout.addWidget(self.content_edit)

        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(ENTITY_NAMES)
        if entity_type in ENTITY_NAMES:
            self.type_combo.setCurrentIndex(ENTITY_NAMES.index(entity_type))
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def get_data(self):
        return self.title_edit.text(), self.content_edit.toPlainText(), self.type_combo.currentText()


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
            add_menu = QMenu("Add", self)
            for etype in ENTITY_NAMES:
                act = QAction(etype, self)
                act.triggered.connect(lambda checked, t=etype: self.add_node(scene_pos, t))
                add_menu.addAction(act)
            menu.addMenu(add_menu)

        menu.exec(self.viewport().mapToGlobal(pos))

    def edit_node(self, node: NodeItem):
        dialog = NodeEditDialog(node.title, node.content, node.entity_type, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_title, new_content, new_type = dialog.get_data()
            node.title = new_title
            node.content = new_content
            node.entity_type = new_type
            node.update()
            for n_data in self.graph_data["nodes"]:
                if n_data["id"] == node.id:
                    n_data["title"] = new_title
                    n_data["content"] = new_content
                    n_data["entity_type"] = new_type
                    break

    def add_node(self, scene_pos, entity_type="Custom"):
        node = NodeItem(title="New node", entity_type=entity_type)
        node.setPos(scene_pos)
        self._scene.addItem(node)
        node_data = {
            "id": node.id,
            "title": node.title,
            "content": node.content,
            "entity_type": node.entity_type,
            "x": scene_pos.x(),
            "y": scene_pos.y(),
        }
        self.graph_data["nodes"].append(node_data)
        self.nodeAdded.emit(node_data)
        return node

    def add_edge(self, source_node, target_node, source_port="right", target_port="left"):
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
                        "entity_type": item.entity_type,
                        "x": item.pos().x(),
                        "y": item.pos().y(),
                    }
                )
            elif isinstance(item, EdgeItem):
                edges.append(
                    {
                        "source": item.source.id,
                        "target": item.target.id,
                        "source_port": item.source_port,
                        "target_port": item.target_port,
                    }
                )
        return {"nodes": nodes, "edges": edges}

    def from_dict(self, data):
        self._scene.clear()
        self.graph_data = {"nodes": [], "edges": []}
        node_map = {}
        for n in data.get("nodes", []):
            nid = str(n.get("id", uuid.uuid4().hex))
            node = NodeItem(
                title=n.get("title", "Node"),
                content=n.get("content", ""),
                entity_type=n.get("entity_type", "Custom"),
                node_id=nid,
            )
            node.setPos(n.get("x", 0), n.get("y", 0))
            self._scene.addItem(node)
            node_map[nid] = node
            self.graph_data["nodes"].append(
                {
                    "id": node.id,
                    "title": node.title,
                    "content": node.content,
                    "entity_type": node.entity_type,
                    "x": node.pos().x(),
                    "y": node.pos().y(),
                }
            )
        for e in data.get("edges", []):
            src = node_map.get(str(e.get("source", "")))
            tgt = node_map.get(str(e.get("target", "")))
            if src and tgt:
                sp = e.get("source_port", "right")
                tp = e.get("target_port", "left")
                edge = EdgeItem(src, tgt, sp, tp)
                self._scene.addItem(edge)
                self.graph_data["edges"].append(
                    {
                        "source": src.id,
                        "target": tgt.id,
                        "source_port": sp,
                        "target_port": tp,
                    }
                )

    def save_to_json(self, filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    def load_from_json(self, filepath):
        with open(filepath, encoding="utf-8") as f:
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
