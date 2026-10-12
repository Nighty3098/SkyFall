import math
from dataclasses import dataclass

import networkx as nx

LAYOUT_ALGORITHMS = {
    "spring": "Force-directed (Spring)",
    "kamada_kawai": "Kamada-Kawai",
    "shell": "Shell (Circular)",
    "spectral": "Spectral",
    "circular": "Circular",
    "hierarchical": "Hierarchical (Top-Down)",
    "topdown": "Top-Down Tree",
    "tree": "Tree",
}

# Default node footprint used when placing nodes automatically.
NODE_WIDTH = 160.0
NODE_HEIGHT = 120.0


@dataclass
class LayoutResult:
    positions: dict[str, tuple[float, float]]


def compute_layout(
    nodes: list[dict],
    edges: list[dict],
    algorithm: str = "spring",
    scale: float = 300.0,
) -> LayoutResult:
    g = nx.Graph()

    for node in nodes:
        g.add_node(node["id"])

    for edge in edges:
        g.add_edge(edge["source"], edge["target"])

    if len(g.nodes) == 0:
        return LayoutResult(positions={})

    if (
        algorithm == "hierarchical"
        or algorithm == "tree"
        or algorithm == "topdown"
        or algorithm == "hierarchical_tree"
        or algorithm == "tree_topdown"
    ):
        res = compute_hierarchical_layout(nodes, edges, direction="down", scale=1.0)
        return res
    if algorithm == "spring":
        pos = nx.spring_layout(g, k=2.0, iterations=50, seed=42)
    elif algorithm == "kamada_kawai":
        try:
            pos = nx.kamada_kawai_layout(g)
        except ImportError:
            pos = nx.spring_layout(g, k=2.0, iterations=50, seed=42)
    elif algorithm == "shell":
        pos = nx.shell_layout(g)
    elif algorithm == "spectral":
        pos = nx.spectral_layout(g)
    elif algorithm == "circular":
        pos = nx.circular_layout(g)
    else:
        pos = nx.spring_layout(g, k=2.0, iterations=50, seed=42)

    positions = {}
    for node_id, (x, y) in pos.items():
        positions[node_id] = (float(x * scale), float(y * scale))

    return LayoutResult(positions=positions)


# ── Automatic placement ───────────────────────────────────────────────
#
# Nodes are stored by their top-left corner (``NodeItem.pos``), while layouts
# and arcs are easier to reason about from a node centre.  The helpers below
# therefore speak in top-left rectangles ``(x, y, w, h)`` and take anchor
# points as centres.


def node_rect(x, y, w=NODE_WIDTH, h=NODE_HEIGHT):
    """Return a ``(x, y, w, h)`` rectangle for a node top-left position."""
    return (float(x), float(y), float(w), float(h))


def rects_overlap(a, b, padding=0.0):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (
        ax + aw + padding <= bx
        or bx + bw + padding <= ax
        or ay + ah + padding <= by
        or by + bh + padding <= ay
    )


def rect_center(rect):
    x, y, w, h = rect
    return (x + w / 2.0, y + h / 2.0)


def graph_centroid(occupied):
    """Centre of mass of a list of ``(x, y, w, h)`` rectangles."""
    if not occupied:
        return (0.0, 0.0)
    cx = sum(x + w / 2.0 for x, _, w, _ in occupied) / len(occupied)
    cy = sum(y + h / 2.0 for _, y, _, h in occupied) / len(occupied)
    return (cx, cy)


def find_free_slot(
    occupied,
    anchor=(0.0, 0.0),
    size=(NODE_WIDTH, NODE_HEIGHT),
    radius=240.0,
    angle_start=-90.0,
    angle_step=30.0,
    radius_growth=130.0,
    max_rings=16,
    padding=36.0,
):
    """Place a node of ``size`` near ``anchor`` without overlapping.

    ``anchor`` is the reference point (usually a parent node centre) and the
    search walks expanding rings of angles around it, returning the first
    top-left position whose rectangle clears every entry in ``occupied``.
    """
    w, h = size
    ax, ay = anchor
    for ring in range(max_rings):
        r = radius + ring * radius_growth
        steps = max(1, int(round(360.0 / angle_step)))
        phase = angle_start + ring * angle_step / 2.0
        for i in range(steps):
            angle = math.radians(phase + i * angle_step)
            cx = ax + r * math.cos(angle)
            cy = ay + r * math.sin(angle)
            rect = (cx - w / 2.0, cy - h / 2.0, w, h)
            if all(not rects_overlap(rect, o, padding) for o in occupied):
                return (rect[0], rect[1])
    # Fallback: one more ring directly below the anchor.
    return (ax - w / 2.0, ay + radius + max_rings * radius_growth)


def child_arc_positions(
    parent_pos,
    count,
    parent_size=(NODE_WIDTH, NODE_HEIGHT),
    child_size=(NODE_WIDTH, NODE_HEIGHT),
    radius=None,
    arc_deg=None,
    spacing=48.0,
    min_radius=220.0,
):
    if count <= 0:
        return []
    pw, ph = parent_size
    cw, ch = child_size
    try:
        if hasattr(parent_pos, "x") and hasattr(parent_pos, "y"):
            px, py = parent_pos.x() + pw / 2.0, parent_pos.y() + ph / 2.0
        elif isinstance(parent_pos, (tuple, list)) and len(parent_pos) >= 2:
            try:
                if hasattr(parent_pos, "x") and hasattr(parent_pos, "y"):
                    px, py = parent_pos.x() + pw / 2.0, parent_pos.y() + ph / 2.0
                elif isinstance(parent_pos, (tuple, list)) and len(parent_pos) >= 2:
                    if hasattr(parent_pos, "x") and hasattr(parent_pos, "y"):
                        px, py = parent_pos.x() + pw / 2.0, parent_pos.y() + ph / 2.0
                    elif isinstance(parent_pos, (tuple, list)) and len(parent_pos) >= 2:
                        if hasattr(parent_pos, "x") and hasattr(parent_pos, "y"):
                            px, py = (
                                parent_pos.x() + pw / 2.0,
                                parent_pos.y() + ph / 2.0,
                            )
                        elif (
                            isinstance(parent_pos, (tuple, list))
                            and len(parent_pos) >= 2
                        ):
                            if hasattr(parent_pos, "x") and hasattr(parent_pos, "y"):
                                px, py = (
                                    parent_pos.x() + pw / 2.0,
                                    parent_pos.y() + ph / 2.0,
                                )
                            elif (
                                isinstance(parent_pos, (tuple, list))
                                and len(parent_pos) >= 2
                            ):
                                if hasattr(parent_pos, "x") and hasattr(
                                    parent_pos, "y"
                                ):
                                    px, py = (
                                        parent_pos.x() + pw / 2.0,
                                        parent_pos.y() + ph / 2.0,
                                    )
                                elif (
                                    isinstance(parent_pos, (tuple, list))
                                    and len(parent_pos) >= 2
                                ):
                                    if hasattr(parent_pos, "x") and hasattr(
                                        parent_pos, "y"
                                    ):
                                        px, py = (
                                            parent_pos.x() + pw / 2.0,
                                            parent_pos.y() + ph / 2.0,
                                        )
                                    elif (
                                        isinstance(parent_pos, (tuple, list))
                                        and len(parent_pos) >= 2
                                    ):
                                        px, py = 0.0, 0.0
                                    else:
                                        px, py = 0.0, 0.0
                                else:
                                    px, py = 0.0, 0.0
                            else:
                                px, py = 0.0, 0.0
                        else:
                            px, py = 0.0, 0.0
                    else:
                        px, py = 0.0, 0.0
                else:
                    px, py = 0.0, 0.0
            except Exception:
                px, py = 0.0, 0.0
        else:
            px, py = 0.0, 0.0
    except Exception:
        px, py = 0.0, 0.0
    if count == 1:
        angles = [-90.0]
    else:
        span = arc_deg if arc_deg is not None else min(150.0 + count * 4.0, 300.0)
        angles = [-span / 2.0 + i * (span / (count - 1)) for i in range(count)]
    if radius is None:
        if count == 1:
            radius = min_radius
        else:
            span = arc_deg if arc_deg is not None else min(150.0 + count * 4.0, 300.0)
            delta = math.radians(span / (count - 1))
            radius = max(min_radius, (cw + spacing) / (2 * math.sin(delta / 2)))
    out = []
    for angle in angles:
        rad = math.radians(angle)
        out.append(
            (
                px + radius * math.cos(rad) - cw / 2.0,
                py + radius * math.sin(rad) - ch / 2.0,
            )
        )
    return out


def compute_hierarchical_layout(
    nodes: list[dict],
    edges: list[dict],
    root_id: str | None = None,
    direction: str = "down",
    h_spacing: float = 90.0,
    v_spacing: float = 70.0,
    scale: float = 1.0,
) -> LayoutResult:
    if not nodes:
        return LayoutResult(positions={})
    g = nx.Graph()
    for n in nodes:
        g.add_node(n["id"])
    for e in edges:
        g.add_edge(e["source"], e["target"])

    # determine root
    start = nodes[0]["id"]
    if root_id and root_id in g:
        start = root_id
    else:
        deg = {nid: g.degree(nid) for nid in g.nodes}
        if deg:
            maxd = -1
            cand = start
            for nid, d in deg.items():
                if d > maxd:
                    maxd = d
                    cand = nid
            start = cand

    # BFS
    from collections import deque

    level = {start: 0}
    q = deque([start])
    visited = {start}
    while q:
        cur = q.popleft()
        for nb in g.neighbors(cur):
            if nb not in visited:
                visited.add(nb)
                level[nb] = level[cur] + 1
                q.append(nb)
    for nid in g.nodes:
        if nid not in level:
            level[nid] = 0

    by_level = {}
    for nid, lv in level.items():
        by_level.setdefault(lv, []).append(nid)

    positions = {}
    for lv, lst in by_level.items():
        count = len(lst)
        total_w = (count - 1) * h_spacing if count > 1 else 0
        start_x = -total_w / 2
        y = lv * v_spacing if direction == "down" else -lv * v_spacing
        for i, nid in enumerate(lst):
            x = start_x + i * h_spacing
            positions[nid] = (x * scale, y * scale)
    return LayoutResult(positions=positions)
