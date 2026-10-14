"""Bridge between analysis graphs (networkx) and the main SkyFall GraphWidget.

Covers two gaps:
- TG Analyzer exports (GraphML / GEXF / node-link JSON / CSV) -> dict that
  ``GraphWidget.from_dict`` understands (with auto-layout, since TG exports
  carry no positions).
- Main graph -> PNG / SVG image export via offscreen scene rendering.
"""

import csv
import json
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

import networkx as nx
from loguru import logger
from networkx.readwrite import json_graph

# File extensions ``load_graph_file`` can read (used by the import dialog and
# by drag & drop onto the graph canvas).
GRAPH_FILE_SUFFIXES = (".json", ".graphml", ".gexf", ".csv")
GRAPH_FILE_FILTER = "Graphs (*.json *.graphml *.gexf *.csv)"

# TG Analyzer node ``node_type`` -> SkyFall entity type
TG_NODE_ENTITY = {
    "user": "Person",
    "channel": "Organization",
    "domain": "Domain",
}

# TG Analyzer ``edge_type`` -> SkyFall relationship type
TG_EDGE_RELATIONSHIP = {
    "member": "member_of",
    "replier": "communicates_with",
    "forwarded": "linked_to",
    "discussion_reply": "communicates_with",
    "mentions": "linked_to",
    "shared_members": "associated_with",
    "linked_chat": "linked_to",
}

_USER_CONTENT_KEYS = (
    "username",
    "first_name",
    "last_name",
    "phone",
    "bot",
    "verified",
    "premium",
    "scam",
    "fake",
    "deleted",
    "business_location",
    "birthday_day",
    "birthday_month",
    "birthday_year",
)


def _tg_node_title(node_id: object, attrs: dict) -> str:
    label = attrs.get("label")
    if label:
        return str(label)
    text = str(node_id)
    for prefix in ("user:", "channel:", "domain:"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break
    return text or str(node_id)


def _tg_node_content(node_id: object, attrs: dict) -> str:
    lines = [f"tg_id: {node_id}"]
    node_type = attrs.get("node_type", "")
    if node_type:
        lines.append(f"type: {node_type}")
    if node_type == "user":
        for key in _USER_CONTENT_KEYS:
            val = attrs.get(key)
            if val is None or val is False or val == "":
                continue
            lines.append(f"{key}: {val}")
    else:
        for key, val in attrs.items():
            if key in ("label", "node_type") or val is None or val == "":
                continue
            lines.append(f"{key}: {val}")
    return "\n".join(lines)


def _tg_edge_label(attrs: dict) -> str:
    edge_type = str(attrs.get("edge_type", "linked"))
    for wkey in ("weight", "weight_forward"):
        w = attrs.get(wkey)
        if isinstance(w, (int, float)) and w > 1:
            return f"{edge_type} x{w}"
    return edge_type


def tg_networkx_to_skyfall(graph: nx.Graph, max_nodes: int = 3000) -> dict:
    """Convert a TG Analyzer networkx graph to ``GraphWidget.from_dict`` format.

    Nodes without positions get a deterministic spring layout. Oversized
    graphs are truncated (channels/domains kept first, then top-degree users).
    """
    nodes = list(graph.nodes(data=True))
    edges = list(graph.edges(data=True))
    logger.debug(f"Converting TG graph: {len(nodes)} nodes, {len(edges)} edges")

    if len(nodes) > max_nodes:
        channels = [n for n in nodes if n[1].get("node_type") != "user"]
        users = [n for n in nodes if n[1].get("node_type") == "user"]
        users.sort(key=lambda n: graph.degree(n[0]), reverse=True)
        keep = {n[0] for n in channels} | {
            n[0] for n in users[: max(0, max_nodes - len(channels))]
        }
        nodes = [n for n in nodes if n[0] in keep]
        edges = [e for e in edges if e[0] in keep and e[1] in keep]
        logger.warning(
            f"TG graph truncated to {len(nodes)} nodes, {len(edges)} edges "
            f"(limit {max_nodes})"
        )

    sub = nx.Graph()
    sub.add_nodes_from(nodes)
    sub.add_edges_from([(u, v) for u, v, _ in edges])

    if len(sub):
        pos = nx.spring_layout(sub, seed=42, iterations=50)
        scale = max(800.0, 60.0 * (len(sub) ** 0.5))
    else:
        pos = {}

    sky_nodes = []
    id_map = {}
    for node_id, attrs in nodes:
        new_id = uuid.uuid4().hex
        id_map[node_id] = new_id
        x, y = pos.get(node_id, (0.0, 0.0))
        evidence = []
        avatar = attrs.get("avatar_path")
        if avatar:
            evidence.append(str(avatar))
        sky_nodes.append(
            {
                "id": new_id,
                "title": _tg_node_title(node_id, attrs),
                "content": _tg_node_content(node_id, attrs),
                "entity_type": TG_NODE_ENTITY.get(attrs.get("node_type", ""), "Custom"),
                "evidence": evidence,
                "x": float(x) * scale,
                "y": float(y) * scale,
                "width": 160,
                "height": 120,
                "color": None,
            }
        )

    sky_edges = []
    for u, v, attrs in edges:
        if u not in id_map or v not in id_map:
            continue
        edge_type = str(attrs.get("edge_type", "linked"))
        sky_edges.append(
            {
                "source": id_map[u],
                "target": id_map[v],
                "source_port": "right",
                "target_port": "left",
                "label": _tg_edge_label(attrs),
                "relationship_type": TG_EDGE_RELATIONSHIP.get(
                    edge_type, "associated_with"
                ),
                "style": "normal",
            }
        )

    return {"nodes": sky_nodes, "edges": sky_edges}


def _coerce_graphml_value(raw: str, attr_type: str):
    try:
        if attr_type == "boolean":
            return raw.strip().lower() in ("true", "1", "yes")
        if attr_type in ("int", "long"):
            return int(float(raw))
        if attr_type in ("float", "double"):
            return float(raw)
    except (ValueError, TypeError):
        pass
    return raw


def _read_graphml_fallback(path: str) -> nx.Graph:
    """Minimal GraphML reader (ElementTree).

    Used when the networkx XML reader is unavailable/broken; covers the
    node/edge attribute shape TG Analyzer exports.
    """
    tree = ET.parse(path)
    root = tree.getroot()
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"

    keys: dict[str, tuple[str, str]] = {}  # key id -> (name, type)
    for key in root.findall(f"{ns}key"):
        keys[key.get("id", "")] = (
            key.get("attr.name", ""),
            key.get("attr.type", "string"),
        )

    graph: nx.Graph = nx.Graph()
    for elem in root.iter():
        tag = elem.tag
        if tag.startswith("{"):
            tag = tag.split("}", 1)[1]
        if tag == "node":
            attrs: dict = {}
            for data in elem.findall(f"{ns}data"):
                name, atype = keys.get(data.get("key", ""), ("", "string"))
                if name:
                    attrs[name] = _coerce_graphml_value(data.text or "", atype)
            graph.add_node(elem.get("id", ""), **attrs)
        elif tag == "edge":
            attrs = {}
            for data in elem.findall(f"{ns}data"):
                name, atype = keys.get(data.get("key", ""), ("", "string"))
                if name:
                    attrs[name] = _coerce_graphml_value(data.text or "", atype)
            graph.add_edge(elem.get("source", ""), elem.get("target", ""), **attrs)
    return graph


def _read_gexf_fallback(path: str) -> nx.Graph:
    """Minimal GEXF 1.2 reader (ElementTree), same fallback purpose."""
    tree = ET.parse(path)
    root = tree.getroot()

    def local(tag: str) -> str:
        return tag.split("}", 1)[1] if tag.startswith("{") else tag

    attr_names: dict[str, dict[str, str]] = {"node": {}, "edge": {}}
    for elem in root.iter():
        if local(elem.tag) == "attributes":
            cls = elem.get("class", "node")
            for attr in elem:
                if local(attr.tag) == "attribute":
                    attr_names.get(cls, {})[attr.get("id", "")] = attr.get("title", "")

    graph: nx.Graph = nx.Graph()
    for elem in root.iter():
        ltag = local(elem.tag)
        if ltag == "node":
            attrs: dict = {}
            for child in elem:
                if local(child.tag) == "attvalues":
                    for av in child:
                        name = attr_names["node"].get(av.get("for", ""), "")
                        if name:
                            attrs[name] = av.get("value", "")
            graph.add_node(elem.get("id", ""), **attrs)
        elif ltag == "edge":
            attrs = {}
            for child in elem:
                if local(child.tag) == "attvalues":
                    for av in child:
                        name = attr_names["edge"].get(av.get("for", ""), "")
                        if name:
                            attrs[name] = av.get("value", "")
            graph.add_edge(elem.get("source", ""), elem.get("target", ""), **attrs)
    return graph


def load_tg_file(path: str) -> nx.Graph:
    """Read a TG Analyzer export file into a networkx graph.

    Supports ``.graphml``, ``.gexf``, node-link ``.json`` and the
    ``*_nodes.csv`` / ``*_edges.csv`` pair (pass the nodes file).
    """
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".graphml":
        try:
            return nx.read_graphml(str(p))
        except Exception as e:
            logger.warning(f"networkx GraphML reader failed ({e}), using fallback.")
            return _read_graphml_fallback(str(p))
    if suffix == ".gexf":
        try:
            return nx.read_gexf(str(p))
        except Exception as e:
            logger.warning(f"networkx GEXF reader failed ({e}), using fallback.")
            return _read_gexf_fallback(str(p))
    if suffix == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "nodes" in data and "links" in data:
            return json_graph.node_link_graph(data)
        if isinstance(data, dict) and "nodes" in data and "edges" in data:
            # node-link written by networkx >= 3.x ("edges" key)
            data = dict(data, links=data["edges"])
            del data["edges"]
            return json_graph.node_link_graph(data)
        # Maybe a SkyFall main-graph JSON? Not convertible here.
        raise ValueError("JSON is not a TG node-link graph (no nodes/links).")
    if suffix == ".csv":
        edges_path = p
        if p.stem.endswith("_nodes"):
            edges_path = p.with_name(p.stem[: -len("_nodes")] + "_edges.csv")
            if not edges_path.exists():
                raise ValueError(f"Edges CSV not found next to {p.name}.")
        elif p.stem.endswith("_edges"):
            raise ValueError("Pass the *_nodes.csv file, not the edges file.")
        graph: nx.Graph = nx.Graph()
        with open(p, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                nid = row.pop("id", None)
                if nid:
                    graph.add_node(nid, **{k: v for k, v in row.items() if v != ""})
        with open(edges_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                src = row.pop("source", None)
                tgt = row.pop("target", None)
                if src and tgt:
                    graph.add_edge(
                        src, tgt, **{k: v for k, v in row.items() if v != ""}
                    )
        return graph
    raise ValueError(f"Unsupported graph file type: {suffix or path}")


def is_skyfall_graph_dict(data: dict) -> bool:
    """Check if a parsed JSON already is a main-graph (from_dict) document."""
    return (
        isinstance(data, dict)
        and isinstance(data.get("nodes"), list)
        and isinstance(data.get("edges"), list)
        and all(isinstance(n, dict) and "title" in n for n in data["nodes"][:1])
    )


def load_graph_file(path: str) -> dict:
    """Load any supported graph file into ``from_dict`` format.

    SkyFall JSON passes through, TG exports get converted + laid out.
    """
    p = Path(path)
    if p.suffix.lower() == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        if is_skyfall_graph_dict(data):
            return data
    graph = load_tg_file(path)
    return tg_networkx_to_skyfall(graph)


def export_scene_image(scene, path: str, scale: int = 2, padding: int = 40) -> str:
    """Render a QGraphicsScene to PNG or SVG (format chosen by suffix)."""
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QImage, QPainter

    suffix = Path(path).suffix.lower()
    if suffix not in (".png", ".svg"):
        raise ValueError("Image path must end with .png or .svg.")

    rect = scene.itemsBoundingRect().adjusted(-padding, -padding, padding, padding)
    if rect.isNull() or rect.width() <= 0 or rect.height() <= 0:
        raise ValueError("Graph is empty, nothing to export.")

    if suffix == ".svg":
        from PySide6.QtSvg import QSvgGenerator

        gen = QSvgGenerator()
        gen.setFileName(path)
        gen.setSize(rect.size().toSize())
        gen.setViewBox(QRectF(0, 0, rect.width(), rect.height()))
        painter = QPainter(gen)
        try:
            scene.render(painter, QRectF(0, 0, rect.width(), rect.height()), rect)
        finally:
            painter.end()
        return path

    width, height = int(rect.width() * scale), int(rect.height() * scale)
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    try:
        painter.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.TextAntialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        scene.render(painter, QRectF(0, 0, width, height), rect)
    finally:
        painter.end()
    if not image.save(path, "PNG"):
        raise OSError(f"Failed to save PNG to {path}.")
    return path
