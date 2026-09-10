import json
import socket
import struct
import threading

from loguru import logger

GRAPH_BRIDGE_HOST = "127.0.0.1"
GRAPH_BRIDGE_PORT = 9878


def _send_msg(sock: socket.socket, data: dict):
    raw = json.dumps(data, ensure_ascii=False, default=str).encode()
    sock.sendall(struct.pack("!I", len(raw)) + raw)


def _recv_msg(sock: socket.socket) -> dict | None:
    header = sock.recv(4)
    if len(header) < 4:
        return None
    length = struct.unpack("!I", header)[0]
    raw = b""
    while len(raw) < length:
        chunk = sock.recv(length - len(raw))
        if not chunk:
            return None
        raw += chunk
    return json.loads(raw)


class GraphBridgeServer:
    def __init__(self):
        self._graph_widget = None
        self._node_item_cls = None
        self._server_sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._worker = None

    def start(self, graph_widget, node_item_cls):
        from PySide6.QtCore import QObject, Signal, Slot

        self._graph_widget = graph_widget
        self._node_item_cls = node_item_cls

        class Worker(QObject):
            execute = Signal(object)

            @Slot(object)
            def on_execute(self, payload):
                func, args, result_container, event = payload
                try:
                    result_container[0] = func(*args)
                except Exception as e:
                    result_container[1] = str(e)
                finally:
                    event.set()

        self._worker = Worker()
        from PySide6.QtCore import Qt

        self._worker.execute.connect(
            self._worker.on_execute, Qt.ConnectionType.BlockingQueuedConnection
        )

        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((GRAPH_BRIDGE_HOST, GRAPH_BRIDGE_PORT))
        self._server_sock.listen(5)
        self._server_sock.settimeout(1.0)
        self._running = True

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info(
            f"Graph bridge listening on {GRAPH_BRIDGE_HOST}:{GRAPH_BRIDGE_PORT}"
        )

    def stop(self):
        self._running = False
        if self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=3)

    def _invoke_on_main(self, func, *args) -> dict:
        result = [None, None]
        event = threading.Event()
        self._worker.execute.emit((func, args, result, event))
        event.wait(timeout=15)
        if result[1]:
            return {"error": result[1]}
        return result[0]

    def _run(self):
        while self._running:
            try:
                client, addr = self._server_sock.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            threading.Thread(
                target=self._handle_client, args=(client,), daemon=True
            ).start()

    def _handle_client(self, sock: socket.socket):
        try:
            while self._running:
                msg = _recv_msg(sock)
                if msg is None:
                    break
                result = self._dispatch(msg)
                _send_msg(sock, result)
        except Exception as e:
            logger.debug(f"Graph bridge client error: {e}")
        finally:
            sock.close()

    def _dispatch(self, msg: dict) -> dict:
        action = msg.get("action")
        try:
            if action == "add_node":
                return self._invoke_on_main(self._add_node, msg)
            if action == "add_edge":
                return self._invoke_on_main(self._add_edge, msg)
            if action == "get_graph":
                return self._invoke_on_main(self._get_graph)
            if action == "get_node":
                return self._invoke_on_main(self._get_node, msg)
            if action == "update_node":
                return self._invoke_on_main(self._update_node, msg)
            if action == "remove_node":
                return self._invoke_on_main(self._remove_node, msg)
            if action == "remove_edge":
                return self._invoke_on_main(self._remove_edge, msg)
            if action == "clear_graph":
                return self._invoke_on_main(self._clear_graph)
            if action == "move_node":
                return self._invoke_on_main(self._move_node, msg)
            if action == "graph_summary":
                return self._invoke_on_main(self._graph_summary)
            if action == "import_dict":
                return self._invoke_on_main(self._import_dict, msg)
            if action == "export_image":
                return self._invoke_on_main(self._export_image, msg)
            return {"error": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"Graph bridge dispatch error: {e}")
            return {"error": str(e)}

    def _add_node(self, msg: dict) -> dict:
        from PySide6.QtCore import QPointF

        gw = self._graph_widget
        if gw is None:
            return {"error": "Graph widget not available"}

        entity_type = msg.get("entity_type", "Custom")
        title = msg.get("title", "")
        content = msg.get("content", "")

        node = gw.add_node(QPointF(0, 0), entity_type=entity_type)
        node.title = title
        node.content = content
        node.update()
        gw.viewport().update()
        return {"node_id": node.id, "title": node.title, "entity_type": entity_type}

    def _add_edge(self, msg: dict) -> dict:
        gw = self._graph_widget
        node_item_cls = self._node_item_cls
        if gw is None:
            return {"error": "Graph widget not available"}

        source_id = msg.get("source_id", "")
        target_id = msg.get("target_id", "")
        relationship = msg.get("relationship", "associated_with")
        label = msg.get("label", "")
        source_port = msg.get("source_port", "right")
        target_port = msg.get("target_port", "left")

        source = target = None
        for item in gw._scene.items():
            if isinstance(item, node_item_cls):
                if item.id == source_id:
                    source = item
                if item.id == target_id:
                    target = item

        if source is None or target is None:
            return {"error": "Node(s) not found in graph"}

        edge = gw.add_edge(source, target, source_port, target_port)
        edge.relationship_type = relationship
        edge.label = label
        edge.update()
        gw.viewport().update()
        return {
            "source_id": source_id,
            "target_id": target_id,
            "relationship": relationship,
            "label": label,
            "source_port": source_port,
            "target_port": target_port,
        }

    def _get_graph(self) -> dict:
        gw = self._graph_widget
        if gw is None:
            return {"error": "Graph widget not available"}
        return gw.to_dict()

    def _find_node(self, node_id: str):
        from src.libs.graph_lib import NodeItem

        gw = self._graph_widget
        if gw is None:
            return None
        for item in gw._scene.items():
            if isinstance(item, NodeItem) and item.id == node_id:
                return item
        return None

    def _get_node(self, msg: dict) -> dict:
        node = self._find_node(msg.get("node_id", ""))
        if node is None:
            return {"error": "Node not found"}
        return {
            "id": node.id,
            "title": node.title,
            "content": node.content,
            "entity_type": node.entity_type,
            "evidence": node.evidence,
            "x": node.pos().x(),
            "y": node.pos().y(),
            "edges": [
                {
                    "source": e.source.id,
                    "target": e.target.id,
                    "relationship": e.relationship_type,
                    "label": e.label,
                }
                for e in node._connected_edges()
            ],
        }

    def _update_node(self, msg: dict) -> dict:
        node = self._find_node(msg.get("node_id", ""))
        if node is None:
            return {"error": "Node not found"}

        if "title" in msg:
            node.title = msg["title"]
        if "content" in msg:
            node.content = msg["content"]
        if "entity_type" in msg:
            node.entity_type = msg["entity_type"]
        node.update()
        self._graph_widget.viewport().update()
        return {"id": node.id, "title": node.title, "entity_type": node.entity_type}

    def _move_node(self, msg: dict) -> dict:
        node = self._find_node(msg.get("node_id", ""))
        if node is None:
            return {"error": "Node not found"}

        x = msg.get("x")
        y = msg.get("y")
        if x is None or y is None:
            return {"error": "x and y coordinates are required"}

        from PySide6.QtCore import QPointF

        node.setPos(QPointF(float(x), float(y)))
        node.update()
        for edge in node._connected_edges():
            edge.adjust()
        self._graph_widget.viewport().update()
        return {
            "node_id": node.id,
            "title": node.title,
            "x": node.pos().x(),
            "y": node.pos().y(),
        }

    def _remove_node(self, msg: dict) -> dict:
        from src.libs.graph_lib import EdgeItem

        gw = self._graph_widget
        node = self._find_node(msg.get("node_id", ""))
        if node is None:
            return {"error": "Node not found"}

        edges_to_remove = [
            e
            for e in gw._scene.items()
            if isinstance(e, EdgeItem) and (e.source is node or e.target is node)
        ]
        for edge in edges_to_remove:
            gw.remove_edge(edge)
        gw._scene.removeItem(node)
        gw.viewport().update()
        return {"removed": node.id, "edges_removed": len(edges_to_remove)}

    def _remove_edge(self, msg: dict) -> dict:
        from src.libs.graph_lib import EdgeItem

        gw = self._graph_widget
        source_id = msg.get("source_id", "")
        target_id = msg.get("target_id", "")

        for item in gw._scene.items():
            if isinstance(item, EdgeItem):
                if item.source.id == source_id and item.target.id == target_id:
                    gw.remove_edge(item)
                    gw.viewport().update()
                    return {
                        "removed": True,
                        "source_id": source_id,
                        "target_id": target_id,
                    }
        return {"error": "Edge not found"}

    def _clear_graph(self) -> dict:
        gw = self._graph_widget
        if gw is None:
            return {"error": "Graph widget not available"}
        count = len(
            [1 for item in gw._scene.items() if isinstance(item, self._node_item_cls)]
        )
        gw._scene.clear()
        gw.viewport().update()
        return {"cleared": count}

    def _import_dict(self, msg: dict) -> dict:
        gw = self._graph_widget
        if gw is None:
            return {"error": "Graph widget not available"}
        data = msg.get("data", {})
        gw.from_dict(data)
        gw.viewport().update()
        return {
            "imported_nodes": len(data.get("nodes", [])),
            "imported_edges": len(data.get("edges", [])),
        }

    def _export_image(self, msg: dict) -> dict:
        from src.modules.graph_io import export_scene_image

        gw = self._graph_widget
        if gw is None:
            return {"error": "Graph widget not available"}
        path = msg.get("path", "")
        if not path:
            return {"error": "path is required"}
        try:
            saved = export_scene_image(gw.scene(), path)
            return {"saved": saved}
        except Exception as e:
            return {"error": str(e)}

    def _graph_summary(self) -> dict:
        from src.libs.graph_lib import EdgeItem, NodeItem

        gw = self._graph_widget
        if gw is None:
            return {"error": "Graph widget not available"}

        nodes = []
        edges = []
        for item in gw._scene.items():
            if isinstance(item, NodeItem):
                nodes.append(
                    {
                        "id": item.id,
                        "title": item.title,
                        "entity_type": item.entity_type,
                    }
                )
            elif isinstance(item, EdgeItem):
                edges.append(
                    {
                        "source": item.source.title,
                        "target": item.target.title,
                        "relationship": item.relationship_type,
                    }
                )

        type_counts = {}
        for n in nodes:
            t = n["entity_type"]
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "entity_types": type_counts,
            "nodes": nodes,
            "edges": edges,
        }


class GraphBridgeClient:
    def __init__(self):
        self._sock: socket.socket | None = None

    def _connect(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((GRAPH_BRIDGE_HOST, GRAPH_BRIDGE_PORT))
        return sock

    def send(self, msg: dict) -> dict:
        sock = self._connect()
        try:
            _send_msg(sock, msg)
            return _recv_msg(sock) or {"error": "No response from graph bridge"}
        finally:
            sock.close()

    def add_node(
        self, title: str, content: str = "", entity_type: str = "Custom"
    ) -> dict:
        return self.send(
            {
                "action": "add_node",
                "title": title,
                "content": content,
                "entity_type": entity_type,
            }
        )

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: str = "associated_with",
        label: str = "",
        source_port: str = "right",
        target_port: str = "left",
    ) -> dict:
        return self.send(
            {
                "action": "add_edge",
                "source_id": source_id,
                "target_id": target_id,
                "relationship": relationship,
                "label": label,
                "source_port": source_port,
                "target_port": target_port,
            }
        )

    def get_graph(self) -> dict:
        return self.send({"action": "get_graph"})

    def get_node(self, node_id: str) -> dict:
        return self.send({"action": "get_node", "node_id": node_id})

    def update_node(
        self,
        node_id: str,
        title: str | None = None,
        content: str | None = None,
        entity_type: str | None = None,
    ) -> dict:
        msg: dict = {"action": "update_node", "node_id": node_id}
        if title is not None:
            msg["title"] = title
        if content is not None:
            msg["content"] = content
        if entity_type is not None:
            msg["entity_type"] = entity_type
        return self.send(msg)

    def move_node(self, node_id: str, x: float, y: float) -> dict:
        return self.send({"action": "move_node", "node_id": node_id, "x": x, "y": y})

    def remove_node(self, node_id: str) -> dict:
        return self.send({"action": "remove_node", "node_id": node_id})

    def remove_edge(self, source_id: str, target_id: str) -> dict:
        return self.send(
            {"action": "remove_edge", "source_id": source_id, "target_id": target_id}
        )

    def clear_graph(self) -> dict:
        return self.send({"action": "clear_graph"})

    def graph_summary(self) -> dict:
        return self.send({"action": "graph_summary"})

    def import_dict(self, data: dict) -> dict:
        return self.send({"action": "import_dict", "data": data})

    def export_image(self, path: str) -> dict:
        return self.send({"action": "export_image", "path": path})
