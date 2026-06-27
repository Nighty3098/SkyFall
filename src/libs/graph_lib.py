import json
import os
import sys
import uuid

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt, QUrl, Signal
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QDesktopServices,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QTextOption,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QGraphicsDropShadowEffect,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
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
    def __init__(
        self, title="Node", content="", entity_type="Custom", node_id=None, parent=None
    ):
        super().__init__(parent)
        self.id = node_id if node_id is not None else uuid.uuid4().hex
        self.title = title
        self.content = content
        self.entity_type = entity_type if entity_type in ENTITY_NAMES else "Custom"
        self.evidence = []
        self._edges = []
        self._width = 160
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

    def _get_height(self):
        if self.entity_type == "Evidence":
            return 130 + max(0, len(self.evidence) - 1) * 18
        return 100

    def boundingRect(self):
        m = self._port_radius + 2
        return QRectF(-m, -m, self._width + 2 * m, self._get_height() + 2 * m)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = _theme_colors()

        rect = QRectF(0, 0, self._width, self._get_height()).adjusted(1, 1, -1, -1)
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

        y_offset = 48

        if self.entity_type == "Evidence" and self.evidence:
            painter.setPen(c["card_content"])
            font_item = QFont("Segoe UI", 8)
            painter.setFont(font_item)
            for i, ev_path in enumerate(self.evidence):
                label = (
                    os.path.basename(ev_path) if os.path.exists(ev_path) else ev_path
                )
                if len(label) > 22:
                    label = label[:19] + "..."
                item_rect = QRectF(12, y_offset, self._width - 24, 16)
                painter.drawText(
                    item_rect,
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    f"• {label}",
                )
                y_offset += 18
        elif self.content:
            painter.setPen(c["card_content"])
            font_content = QFont("Segoe UI", 8)
            painter.setFont(font_content)
            ch = self._get_height() - y_offset - 8
            content_rect = QRectF(10, y_offset, self._width - 20, ch)
            opt = QTextOption()
            opt.setWrapMode(QTextOption.WrapMode.WordWrap)
            painter.drawText(content_rect, self.content, opt)

        if self.evidence:
            emoji = "📎"
            clip_rect = QRectF(self._width - 26, 7, 18, 16)
            painter.setPen(QColor("#ffffff"))
            font_clip = QFont("Segoe UI", 9)
            painter.setFont(font_clip)
            painter.drawText(
                clip_rect,
                Qt.AlignmentFlag.AlignCenter,
                emoji,
            )

        painter.setPen(Qt.PenStyle.NoPen)
        for _, pos in self._ports().items():
            painter.setBrush(QBrush(c["port_color"]))
            painter.drawEllipse(pos, self._port_radius, self._port_radius)

    def _ports(self):
        h = self._get_height()
        return {
            "left": QPointF(0, h / 2),
            "right": QPointF(self._width, h / 2),
            "top": QPointF(self._width / 2, 0),
            "bottom": QPointF(self._width / 2, h),
        }

    def port_pos(self, name):
        return self._ports()[name]

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self._connected_edges():
                edge.adjust()
        return super().itemChange(change, value)

    def add_edge_ref(self, edge):
        if edge not in self._edges:
            self._edges.append(edge)

    def remove_edge_ref(self, edge):
        if edge in self._edges:
            self._edges.remove(edge)

    def _connected_edges(self):
        return list(self._edges)

    def _port_at_pos(self, pos):
        r = self._port_radius + 4
        for name, p in self._ports().items():
            if (pos - p).manhattanLength() < r:
                return name
        return None

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self._port_at_pos(
            event.pos()
        ):
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
                        tp = (
                            target_node._port_at_pos(
                                target_node.mapFromScene(event.scenePos())
                            )
                            or "left"
                        )
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
        label="",
        parent=None,
    ):
        super().__init__(parent)
        self.source = source
        self.target = target
        self.source_port = source_port
        self.target_port = target_port
        self.label = label
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

        if self.label:
            path_length = self.path().length()
            if path_length > 40:
                mid = self.path().pointAtPercent(0.5)
                painter.save()
                fm = painter.fontMetrics()
                text_w = fm.horizontalAdvance(self.label) + 12
                text_h = fm.height() + 6
                bg = QRectF(mid.x() - text_w / 2, mid.y() - text_h / 2, text_w, text_h)
                painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(bg, 4, 4)
                painter.setPen(QPen(c["card_title"]))
                painter.drawText(bg, Qt.AlignmentFlag.AlignCenter, self.label)
                painter.restore()


class NodeEditDialog(QDialog):
    def __init__(
        self, title="", content="", entity_type="Custom", evidence=None, parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle("Edit Node")
        self.setModal(True)

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
            NodeEditDialog QLineEdit::placeholder,
            NodeEditDialog QPlainTextEdit::placeholder {{
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
        self.content_edit.setMinimumHeight(80)
        layout.addWidget(self.content_edit)

        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(ENTITY_NAMES)
        if entity_type in ENTITY_NAMES:
            self.type_combo.setCurrentIndex(ENTITY_NAMES.index(entity_type))
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)

        evidence_label = QLabel("Evidence:")
        layout.addWidget(evidence_label)

        self.evidence_list = QListWidget()
        self.evidence_list.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.evidence_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.evidence_list.customContextMenuRequested.connect(
            self._evidence_context_menu
        )
        self.evidence_list.itemDoubleClicked.connect(self._open_evidence)
        evidence = evidence or []
        for ev_path in evidence:
            label = os.path.basename(ev_path) if os.path.exists(ev_path) else ev_path
            self.evidence_list.addItem(f"{label}\n{ev_path}")
        layout.addWidget(self.evidence_list)

        ev_btn_layout = QHBoxLayout()
        btn_add_file = QPushButton("Add File")
        btn_add_file.clicked.connect(self._add_file)
        btn_add_url = QPushButton("Add URL")
        btn_add_url.clicked.connect(self._add_url)
        btn_remove_ev = QPushButton("Remove Selected")
        btn_remove_ev.clicked.connect(self._remove_evidence)
        ev_btn_layout.addWidget(btn_add_file)
        ev_btn_layout.addWidget(btn_add_url)
        ev_btn_layout.addWidget(btn_remove_ev)
        layout.addLayout(ev_btn_layout)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _add_file(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Evidence Files")
        for f in files:
            self.evidence_list.addItem(f"{os.path.basename(f)}\n{f}")

    def _add_url(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add URL")
        ss = QApplication.instance().styleSheet()
        dark = "#0A0A0A" in ss
        bg = "#0A0A0A" if dark else "#F5F5F5"
        surface = "#161616" if dark else "#E8E8E8"
        border = "#262626" if dark else "#D0D0D0"
        text = "#C1C1C1" if dark else "#3A3A3A"
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            QLineEdit {{
                border-radius: 10px;
                border: 1px solid {border};
                background-color: {surface};
                color: {text};
                padding: 5px;
                selection-background-color: {text};
                selection-color: {bg};
            }}
            QPushButton {{
                border-radius: 10px;
                border: 1px solid {border};
                background-color: {surface};
                color: {text};
                padding: 6px 16px;
                min-height: 24px;
            }}
            QPushButton:hover {{
                background-color: {border};
                color: {text};
            }}
            QPushButton:pressed {{
                background-color: {text};
                color: {bg};
            }}
        """)
        layout = QVBoxLayout(dialog)
        line_edit = QLineEdit()
        line_edit.setPlaceholderText("https://example.com/file.pdf")
        layout.addWidget(line_edit)
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(dialog.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(dialog.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        if dialog.exec() == QDialog.DialogCode.Accepted and line_edit.text().strip():
            self.evidence_list.addItem(
                f"{line_edit.text().strip()}\n{line_edit.text().strip()}"
            )

    def _remove_evidence(self):
        for item in self.evidence_list.selectedItems():
            self.evidence_list.takeItem(self.evidence_list.row(item))

    def _evidence_context_menu(self, pos):
        item = self.evidence_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        delete_act = QAction("Delete", self)
        delete_act.triggered.connect(lambda: self._remove_evidence())
        menu.addAction(delete_act)
        menu.exec(self.evidence_list.viewport().mapToGlobal(pos))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete and self.evidence_list.hasFocus():
            self._remove_evidence()
        else:
            super().keyPressEvent(event)

    def _open_evidence(self, item):
        path = item.text().split("\n", 1)[-1]
        url = QUrl.fromLocalFile(path) if os.path.exists(path) else QUrl(path)
        QDesktopServices.openUrl(url)

    def get_data(self):
        evidence = []
        for i in range(self.evidence_list.count()):
            path = self.evidence_list.item(i).text().split("\n", 1)[-1]
            evidence.append(path)
        return (
            self.title_edit.text(),
            self.content_edit.toPlainText(),
            self.type_combo.currentText(),
            evidence,
        )


class GraphWidget(QGraphicsView):
    nodeAdded = Signal(object)
    edgeAdded = Signal(object)

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

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, pos):
        scene_pos = self.mapToScene(pos)
        item = self._scene.itemAt(scene_pos, self.transform())
        menu = QMenu(self)

        if isinstance(item, EdgeItem):
            label_action = QAction("Edit Label", self)
            label_action.triggered.connect(lambda: self.edit_edge_label(item))
            menu.addAction(label_action)
            menu.addSeparator()
            delete_action = QAction("Delete Edge", self)
            delete_action.triggered.connect(lambda: self.remove_edge(item))
            menu.addAction(delete_action)
        elif isinstance(item, NodeItem):
            edit_action = QAction("Edit", self)
            edit_action.triggered.connect(lambda: self.edit_node(item))
            menu.addAction(edit_action)
            attach_action = QAction("Attach Evidence", self)
            attach_action.triggered.connect(lambda: self.edit_node(item))
            menu.addAction(attach_action)
            menu.addSeparator()
            delete_action = QAction("Delete Node", self)
            delete_action.triggered.connect(lambda: self.remove_node(item))
            menu.addAction(delete_action)
        else:
            add_menu = QMenu("Add", self)
            for etype in ENTITY_NAMES:
                act = QAction(etype, self)
                act.triggered.connect(
                    lambda checked, t=etype: self.add_node(scene_pos, t)
                )
                add_menu.addAction(act)
            menu.addMenu(add_menu)

        menu.exec(self.viewport().mapToGlobal(pos))

    def edit_node(self, node: NodeItem):
        dialog = NodeEditDialog(
            node.title, node.content, node.entity_type, node.evidence, self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_title, new_content, new_type, new_evidence = dialog.get_data()
            node.title = new_title
            node.content = new_content
            node.entity_type = new_type
            node.evidence = new_evidence
            node.prepareGeometryChange()
            node.update()

    def edit_edge_label(self, edge: EdgeItem):
        from PySide6.QtWidgets import QInputDialog

        label, ok = QInputDialog.getText(
            self, "Edit Edge Label", "Label:", text=edge.label
        )
        if ok:
            edge.label = label
            edge.update()

    def add_node(self, scene_pos, entity_type="Custom"):
        node = NodeItem(title="New node", entity_type=entity_type)
        node.setPos(scene_pos)
        self._scene.addItem(node)
        self.nodeAdded.emit(node)
        return node

    def add_edge(
        self, source_node, target_node, source_port="right", target_port="left"
    ):
        edge = EdgeItem(source_node, target_node, source_port, target_port)
        self._scene.addItem(edge)
        source_node.add_edge_ref(edge)
        target_node.add_edge_ref(edge)
        self.edgeAdded.emit(edge)
        return edge

    def remove_node(self, node: NodeItem):
        for edge in node._connected_edges():
            self.remove_edge(edge)
        self._scene.removeItem(node)

    def remove_edge(self, edge: EdgeItem):
        edge.source.remove_edge_ref(edge)
        edge.target.remove_edge_ref(edge)
        self._scene.removeItem(edge)

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
                        "evidence": item.evidence,
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
                        "label": item.label,
                    }
                )
        return {"nodes": nodes, "edges": edges}

    def from_dict(self, data):
        self._scene.clear()
        node_map = {}
        for n in data.get("nodes", []):
            nid = str(n.get("id", uuid.uuid4().hex))
            node = NodeItem(
                title=n.get("title", "Node"),
                content=n.get("content", ""),
                entity_type=n.get("entity_type", "Custom"),
                node_id=nid,
            )
            node.evidence = n.get("evidence", [])
            node.setPos(n.get("x", 0), n.get("y", 0))
            self._scene.addItem(node)
            node_map[nid] = node
        for e in data.get("edges", []):
            src = node_map.get(str(e.get("source", "")))
            tgt = node_map.get(str(e.get("target", "")))
            if src and tgt:
                sp = e.get("source_port", "right")
                tp = e.get("target_port", "left")
                edge = EdgeItem(src, tgt, sp, tp, label=e.get("label", ""))
                self._scene.addItem(edge)
                src.add_edge_ref(edge)
                tgt.add_edge_ref(edge)

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
