import json
import socket
import struct
import threading
import time

from loguru import logger

from src.security import read_token, tokens_equal

GRAPH_BRIDGE_HOST = "127.0.0.1"
GRAPH_BRIDGE_PORT = 9878
MAX_FRAME_SIZE = 1024 * 1024
MAX_CLIENTS = 16
CLIENT_READ_TIMEOUT = 10.0
FRAME_READ_TIMEOUT = 10.0
MAIN_THREAD_INVOKE_TIMEOUT = 15.0


def _recv_exact(
    sock: socket.socket, size: int, deadline: float | None = None
) -> bytes | None:
    chunks = []
    remaining = size
    original_timeout = sock.gettimeout()
    try:
        while remaining:
            if deadline is not None:
                time_left = deadline - time.monotonic()
                if time_left <= 0:
                    raise TimeoutError("graph bridge frame read timed out")
                if original_timeout is None or original_timeout <= 0:
                    sock.settimeout(time_left)
                else:
                    sock.settimeout(min(original_timeout, time_left))
            chunk = sock.recv(remaining)
            if not chunk:
                return None
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)
    finally:
        if deadline is not None:
            sock.settimeout(original_timeout)


def _send_msg(sock: socket.socket, data: dict):
    raw = json.dumps(data, ensure_ascii=False, default=str).encode()
    sock.sendall(struct.pack("!I", len(raw)) + raw)


def _recv_msg(sock: socket.socket) -> dict | None:
    deadline = time.monotonic() + FRAME_READ_TIMEOUT
    header = _recv_exact(sock, 4, deadline)
    if header is None:
        return None
    length = struct.unpack("!I", header)[0]
    if length > MAX_FRAME_SIZE:
        raise ValueError(f"Graph bridge frame exceeds {MAX_FRAME_SIZE} bytes")
    raw = _recv_exact(sock, length, deadline)
    if raw is None:
        return None
    return json.loads(raw)


class _Invocation:
    def __init__(self, func, args):
        self.func = func
        self.args = args
        self.result = None
        self.error = None
        self.event = threading.Event()
        self._lock = threading.Lock()
        self._cancelled = False
        self._started = False

    def execute(self):
        with self._lock:
            if self._cancelled:
                self.event.set()
                return
            self._started = True
        try:
            self.result = self.func(*self.args)
        except Exception as e:
            self.error = str(e)
        finally:
            self.event.set()

    def cancel_if_queued(self):
        with self._lock:
            if not self._started:
                self._cancelled = True


class GraphBridgeServer:
    def __init__(self):
        self._graph_widget = None
        self._node_item_cls = None
        self._server_sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._worker = None
        self._token = ""
        self._stop_event = threading.Event()
        self._client_lock = threading.Lock()
        self._clients: dict[socket.socket, threading.Thread] = {}

    def start(self, graph_widget, node_item_cls, token: str = ""):
        from PySide6.QtCore import QObject, Signal, Slot

        self._graph_widget = graph_widget
        self._node_item_cls = node_item_cls
        self._token = token or read_token()

        class Worker(QObject):
            execute = Signal(object)

            @Slot(object)
            def on_execute(self, invocation):
                invocation.execute()

        self._worker = Worker()
        from PySide6.QtCore import Qt

        self._worker.execute.connect(
            self._worker.on_execute, Qt.ConnectionType.QueuedConnection
        )

        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_sock.bind((GRAPH_BRIDGE_HOST, GRAPH_BRIDGE_PORT))
            self._server_sock.listen(MAX_CLIENTS)
            self._server_sock.settimeout(1.0)
            self._stop_event.clear()
            self._running = True

            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
        except Exception:
            self._server_sock.close()
            self._server_sock = None
            raise
        logger.info(
            f"Graph bridge listening on {GRAPH_BRIDGE_HOST}:{GRAPH_BRIDGE_PORT}"
        )

    def stop(self):
        self._running = False
        self._stop_event.set()
        server_sock, self._server_sock = self._server_sock, None
        if server_sock:
            try:
                server_sock.close()
            except Exception:
                pass
        with self._client_lock:
            clients = list(self._clients.items())
        for sock, _ in clients:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass
        thread = self._thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout=3)
        deadline = time.monotonic() + 3
        for _, client_thread in clients:
            if client_thread is not threading.current_thread():
                client_thread.join(timeout=max(0, deadline - time.monotonic()))
        self._thread = None

    def _invoke_on_main(self, func, *args) -> dict:
        invocation = _Invocation(func, args)
        self._worker.execute.emit(invocation)
        deadline = time.monotonic() + MAIN_THREAD_INVOKE_TIMEOUT
        while not invocation.event.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                invocation.cancel_if_queued()
                return {"error": "Graph bridge main-thread invocation timed out"}
            if self._stop_event.wait(min(remaining, 0.1)):
                invocation.cancel_if_queued()
                return {"error": "Graph bridge stopped during main-thread invocation"}
        if invocation.error:
            return {"error": invocation.error}
        return invocation.result

    def _run(self):
        server_sock = self._server_sock
        if server_sock is None:
            return
        while self._running:
            try:
                client, _ = server_sock.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            with self._client_lock:
                if not self._running or len(self._clients) >= MAX_CLIENTS:
                    accepted = False
                else:
                    client.settimeout(CLIENT_READ_TIMEOUT)
                    thread = threading.Thread(
                        target=self._handle_client,
                        args=(client,),
                        daemon=True,
                    )
                    self._clients[client] = thread
                    accepted = True
                    thread.start()
            if not accepted:
                client.close()

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
            with self._client_lock:
                self._clients.pop(sock, None)

    def _dispatch(self, msg: dict) -> dict:
        if not tokens_equal(self._token, msg.get("token")):
            logger.warning("Graph bridge rejected a request with an invalid token")
            return {"error": "unauthorized"}
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
            if action == "apply_layout":
                return self._invoke_on_main(self._apply_layout, msg)
            if action == "build_graph":
                return self._invoke_on_main(self._build, msg)
            if action == "fit_view":
                return self._invoke_on_main(self._fit_view)
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

    def _occupied_rects(self, gw):
        return [
            (item.pos().x(), item.pos().y(), item._width, item._height)
            for item in gw._scene.items()
            if isinstance(item, self._node_item_cls)
        ]

    def _add_node(self, msg: dict) -> dict:
        from PySide6.QtCore import QPointF

        from src.libs.graph_lib import ENTITY_NAMES, normalize_entity_type
        from src.modules.graph_layout import find_free_slot, graph_centroid

        gw = self._graph_widget
        if gw is None:
            return {"error": "Graph widget not available"}

        raw_type = msg.get("entity_type", "Custom") or "Custom"
        entity_type = normalize_entity_type(raw_type)
        if not entity_type:
            return {
                "error": f"Unknown entity_type {raw_type!r}",
                "valid_entity_types": ENTITY_NAMES,
            }

        title = str(msg.get("title", "") or "").strip()
        if not title:
            return {"error": "title is required"}
        content = str(msg.get("content", "") or "")

        # Upsert: reuse a node with the same type and (case-insensitive) title
        # so repeated agent calls enrich the graph instead of duplicating it.
        if not msg.get("allow_duplicate", False):
            for item in gw._scene.items():
                if (
                    isinstance(item, self._node_item_cls)
                    and item.entity_type == entity_type
                    and (item.title or "").strip().lower() == title.lower()
                ):
                    if content and content not in (item.content or ""):
                        item.content = (
                            f"{item.content}\n{content}".strip()
                            if item.content
                            else content
                        )
                        item.update()
                        gw.viewport().update()
                    return {
                        "node_id": item.id,
                        "title": item.title,
                        "entity_type": item.entity_type,
                        "created": False,
                        "deduplicated": True,
                        "position": [item.pos().x(), item.pos().y()],
                    }

        if msg.get("x") is not None and msg.get("y") is not None:
            pos = (float(msg["x"]), float(msg["y"]))
        else:
            rects = self._occupied_rects(gw)
            anchor_item = self._find_node(msg.get("anchor_id", ""))
            if anchor_item is not None:
                anchor = (
                    anchor_item.pos().x() + anchor_item._width / 2.0,
                    anchor_item.pos().y() + anchor_item._height / 2.0,
                )
                pos = find_free_slot(rects, anchor=anchor, radius=250.0)
            else:
                pos = find_free_slot(rects, anchor=graph_centroid(rects), radius=260.0)

        node = gw.add_node(QPointF(pos[0], pos[1]), entity_type=entity_type)
        node.title = title
        node.content = content
        node.update()
        gw.viewport().update()
        return {
            "node_id": node.id,
            "title": node.title,
            "entity_type": entity_type,
            "created": True,
            "deduplicated": False,
            "anchor_id": msg.get("anchor_id", ""),
            "position": [pos[0], pos[1]],
        }

    def _add_edge(self, msg: dict) -> dict:
        from src.libs.graph_lib import (
            PORT_DIR,
            RELATIONSHIP_TYPES,
            EdgeItem,
            auto_ports,
            normalize_relationship,
        )

        gw = self._graph_widget
        if gw is None:
            return {"error": "Graph widget not available"}

        source_id = msg.get("source_id", "")
        target_id = msg.get("target_id", "")
        if not source_id or not target_id:
            return {"error": "source_id and target_id are required"}
        if source_id == target_id:
            return {"error": "self-loops are not allowed"}

        relationship = normalize_relationship(msg.get("relationship"))
        label = str(msg.get("label", "") or "")

        source = self._find_node(source_id)
        target = self._find_node(target_id)
        if source is None or target is None:
            return {"error": "Node(s) not found in graph"}

        # Deduplicate: refresh an existing edge instead of stacking a new one.
        for item in gw._scene.items():
            if isinstance(item, EdgeItem) and {
                item.source.id,
                item.target.id,
            } == {source_id, target_id}:
                item.relationship_type = relationship
                if label:
                    item.label = label
                item.update()
                gw.viewport().update()
                return {
                    "created": False,
                    "duplicate": True,
                    "source_id": source_id,
                    "target_id": target_id,
                    "relationship": relationship,
                    "label": item.label,
                }

        source_port = msg.get("source_port") or ""
        target_port = msg.get("target_port") or ""
        if source_port not in PORT_DIR or target_port not in PORT_DIR:
            source_port, target_port = auto_ports(source, target)

        edge = gw.add_edge(source, target, source_port, target_port)
        edge.relationship_type = relationship
        edge.label = label
        edge.update()
        gw.viewport().update()
        return {
            "created": True,
            "duplicate": False,
            "source_id": source_id,
            "target_id": target_id,
            "relationship": relationship,
            "relationship_known": relationship in RELATIONSHIP_TYPES,
            "label": label,
            "source_port": source_port,
            "target_port": target_port,
        }

    def _apply_layout(self, msg: dict) -> dict:
        from src.libs.graph_lib import EdgeItem
        from src.modules.graph_layout import compute_layout

        gw = self._graph_widget
        if gw is None:
            return {"error": "Graph widget not available"}

        algorithm = msg.get("algorithm") or "spring"
        nodes = []
        edges = []
        node_map = {}
        for item in gw._scene.items():
            if isinstance(item, self._node_item_cls):
                nodes.append(
                    {
                        "id": item.id,
                        "title": item.title,
                        "x": item.pos().x(),
                        "y": item.pos().y(),
                    }
                )
                node_map[item.id] = item
            elif isinstance(item, EdgeItem):
                edges.append({"source": item.source.id, "target": item.target.id})

        if not nodes:
            return {"error": "Graph is empty"}

        result = compute_layout(nodes, edges, algorithm=algorithm)

        gw.push_undo_state()
        positions = {}
        for node_id, (x, y) in result.positions.items():
            node = node_map.get(node_id)
            if node is None:
                continue
            node.setPos(x - node._width / 2.0, y - node._height / 2.0)
            positions[node_id] = [node.pos().x(), node.pos().y()]

        fitted = False
        if msg.get("fit_view", True):
            fitted = gw.fit_to_view()
        gw.viewport().update()
        return {
            "algorithm": algorithm,
            "laid_out": len(positions),
            "fitted": fitted,
            "positions": positions,
        }

    def _build(self, msg: dict) -> dict:
        """Create a batch of nodes and edges as a single undo step."""
        gw = self._graph_widget
        if gw is None:
            return {"error": "Graph widget not available"}
        gw.begin_bulk_edit()
        try:
            return self._build_impl(msg)
        finally:
            gw.end_bulk_edit()

    def _build_impl(self, msg: dict) -> dict:
        """Create a batch of nodes and edges in one call.

        Each node spec may carry a ``ref`` (temporary id) and an ``anchor``
        pointing at an existing node id or an earlier ``ref``; edges reference
        refs or node ids.  Returns the mapping of refs to real node ids.
        """
        gw = self._graph_widget
        if gw is None:
            return {"error": "Graph widget not available"}

        nodes = msg.get("nodes") or []
        edges = msg.get("edges") or []
        if not isinstance(nodes, list):
            return {"error": "nodes must be a list"}

        ref_map: dict[str, str] = {}
        created_nodes = []
        for spec in nodes:
            if not isinstance(spec, dict):
                return {"error": "each node must be an object"}
            ref = str(spec.get("ref") or spec.get("id") or "").strip()
            anchor = str(spec.get("anchor") or spec.get("anchor_ref") or "").strip()
            anchor = ref_map.get(anchor, anchor)
            sub = {
                "title": spec.get("title", ""),
                "content": spec.get("content", ""),
                "entity_type": spec.get("entity_type", "Custom"),
                "anchor_id": anchor,
                "allow_duplicate": spec.get("allow_duplicate", False),
            }
            if spec.get("x") is not None and spec.get("y") is not None:
                sub["x"] = spec["x"]
                sub["y"] = spec["y"]
            res = self._add_node(sub)
            if res.get("error"):
                return {"error": res["error"], "failed_node": spec}
            if ref:
                ref_map[ref] = res["node_id"]
            created_nodes.append(
                {
                    "ref": ref,
                    "node_id": res["node_id"],
                    "title": res.get("title", ""),
                    "entity_type": res.get("entity_type", ""),
                    "created": res.get("created", True),
                }
            )

        created_edges = []
        for spec in edges:
            if not isinstance(spec, dict):
                return {"error": "each edge must be an object"}
            src = str(spec.get("source") or spec.get("from") or "").strip()
            tgt = str(spec.get("target") or spec.get("to") or "").strip()
            src = ref_map.get(src, src)
            tgt = ref_map.get(tgt, tgt)
            res = self._add_edge(
                {
                    "source_id": src,
                    "target_id": tgt,
                    "relationship": spec.get("relationship", "associated_with"),
                    "label": spec.get("label", ""),
                    "source_port": spec.get("source_port") or "",
                    "target_port": spec.get("target_port") or "",
                }
            )
            entry = {"source": src, "target": tgt}
            if res.get("error"):
                entry["error"] = res["error"]
            else:
                entry["created"] = res.get("created", False)
                entry["relationship"] = res.get("relationship", "")
            created_edges.append(entry)

        gw.viewport().update()
        return {
            "nodes": created_nodes,
            "edges": created_edges,
            "node_ids": ref_map,
            "total_nodes": len(created_nodes),
            "total_edges": len(created_edges),
        }

    def _fit_view(self) -> dict:
        gw = self._graph_widget
        if gw is None:
            return {"error": "Graph widget not available"}
        return {"fitted": gw.fit_to_view()}

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
        gw.clear_graph()
        gw.viewport().update()
        return {"cleared": count}

    def _import_dict(self, msg: dict) -> dict:
        gw = self._graph_widget
        if gw is None:
            return {"error": "Graph widget not available"}
        data = msg.get("data", {})
        gw.push_undo_state()
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
    def __init__(self, token: str = ""):
        self._sock: socket.socket | None = None
        self._token = token or read_token()

    def _connect(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((GRAPH_BRIDGE_HOST, GRAPH_BRIDGE_PORT))
        return sock

    def send(self, msg: dict) -> dict:
        msg = {**msg, "token": self._token}
        sock = self._connect()
        try:
            _send_msg(sock, msg)
            return _recv_msg(sock) or {"error": "No response from graph bridge"}
        finally:
            sock.close()

    def add_node(
        self,
        title: str,
        content: str = "",
        entity_type: str = "Custom",
        anchor_id: str = "",
        allow_duplicate: bool = False,
        x: float | None = None,
        y: float | None = None,
    ) -> dict:
        msg = {
            "action": "add_node",
            "title": title,
            "content": content,
            "entity_type": entity_type,
            "anchor_id": anchor_id,
            "allow_duplicate": allow_duplicate,
        }
        if x is not None and y is not None:
            msg["x"] = x
            msg["y"] = y
        return self.send(msg)

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: str = "associated_with",
        label: str = "",
        source_port: str | None = None,
        target_port: str | None = None,
    ) -> dict:
        return self.send(
            {
                "action": "add_edge",
                "source_id": source_id,
                "target_id": target_id,
                "relationship": relationship,
                "label": label,
                "source_port": source_port or "",
                "target_port": target_port or "",
            }
        )

    def apply_layout(self, algorithm: str = "spring", fit_view: bool = True) -> dict:
        return self.send(
            {
                "action": "apply_layout",
                "algorithm": algorithm,
                "fit_view": fit_view,
            }
        )

    def fit_view(self) -> dict:
        return self.send({"action": "fit_view"})

    def build_graph(self, nodes: list[dict], edges: list[dict]) -> dict:
        return self.send({"action": "build_graph", "nodes": nodes, "edges": edges})

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
