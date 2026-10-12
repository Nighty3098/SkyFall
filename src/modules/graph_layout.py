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


def _target_span(count: int) -> float:
    """Bounding-box side that fits ``count`` nodes without overlap."""
    cell = max(NODE_WIDTH, NODE_HEIGHT)
    cols = max(1, math.ceil(math.sqrt(max(count, 1))))
    gap = cell * 0.35
    return cols * (cell + gap)


def _fit_positions(
    pos: dict[str, tuple[float, float]],
    span: float,
) -> dict[str, tuple[float, float]]:
    """Centre raw layout coordinates and scale them to roughly ``span``."""
    if not pos:
        return {}
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    cx = (min(xs) + max(xs)) / 2.0
    cy = (min(ys) + max(ys)) / 2.0
    largest = max(max(xs) - min(xs), max(ys) - min(ys), 1e-9)
    factor = span / largest
    return {nid: ((x - cx) * factor, (y - cy) * factor) for nid, (x, y) in pos.items()}


def compute_layout(
    nodes: list[dict],
    edges: list[dict],
    algorithm: str = "spring",
    scale: float = 1.0,
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
        return compute_hierarchical_layout(nodes, edges, direction="down", scale=scale)

    count = len(g.nodes)
    span = _target_span(count) * max(scale, 0.01)

    if algorithm == "spring":
        raw = nx.spring_layout(g, k=0.6, iterations=80, seed=42)
    elif algorithm == "kamada_kawai":
        try:
            raw = nx.kamada_kawai_layout(g)
        except ImportError:
            raw = nx.spring_layout(g, k=0.6, iterations=80, seed=42)
    elif algorithm == "shell":
        raw = nx.shell_layout(g)
    elif algorithm == "spectral":
        try:
            raw = nx.spectral_layout(g)
        except Exception:
            raw = nx.spring_layout(g, k=0.6, iterations=80, seed=42)
    elif algorithm == "circular":
        raw = nx.circular_layout(g)
    else:
        raw = nx.spring_layout(g, k=0.6, iterations=80, seed=42)

    fitted = _fit_positions(
        {nid: (float(x), float(y)) for nid, (x, y) in raw.items()}, span
    )
    return LayoutResult(positions=fitted)


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
    h_spacing: float | None = None,
    v_spacing: float | None = None,
    scale: float = 1.0,
) -> LayoutResult:
    """Top-down tree layout (tidy-tree style).

    Parents are centred above their children and siblings get an even,
    node-sized horizontal gap, so the tree reads top-to-bottom without the
    uneven level packing of a plain BFS grid.
    """
    if not nodes:
        return LayoutResult(positions={})

    if h_spacing is None:
        h_spacing = NODE_WIDTH + 40.0
    if v_spacing is None:
        v_spacing = NODE_HEIGHT + 60.0

    g = nx.DiGraph()
    for n in nodes:
        g.add_node(n["id"])
    for e in edges:
        src, tgt = e["source"], e["target"]
        if src in g and tgt in g and src != tgt:
            g.add_edge(src, tgt)

    children = {nid: sorted(g.successors(nid)) for nid in g.nodes}
    roots = [nid for nid in g.nodes if g.in_degree(nid) == 0]
    if root_id and root_id in g:
        roots = [root_id] + [r for r in roots if r != root_id]
    if not roots:
        roots = [max(g.nodes, key=lambda nid: g.out_degree(nid))]

    level: dict[str, int] = {}
    column: dict[str, float] = {}
    visited: set[str] = set()
    next_col = [0.0]

    def assign(nid: str, depth: int, path: frozenset[str]) -> float:
        visited.add(nid)
        level[nid] = depth
        kids = [c for c in children[nid] if c not in visited and c not in path]
        if not kids:
            col = next_col[0]
            next_col[0] += 1.0
        else:
            child_cols = [assign(c, depth + 1, path | {nid}) for c in kids]
            col = (min(child_cols) + max(child_cols)) / 2.0
        column[nid] = col
        return col

    for root in roots:
        if root in visited:
            continue
        assign(root, 0, frozenset())
        next_col[0] += 1.0  # gap between disconnected components

    remaining = [nid for nid in g.nodes if nid not in visited]
    if remaining:
        undirected = g.to_undirected()
        for nid in remaining:
            if nid in visited:
                continue
            component = nx.node_connected_component(undirected, nid)
            start = max(component, key=lambda x: g.out_degree(x))
            assign(start, 0, frozenset())
            next_col[0] += 1.0

    cols = list(column.values())
    centre = (min(cols) + max(cols)) / 2.0 if cols else 0.0

    positions: dict[str, tuple[float, float]] = {}
    for nid, col in column.items():
        x = (col - centre) * h_spacing * scale
        depth = level.get(nid, 0)
        y = depth * v_spacing * scale
        if direction == "up":
            y = -y
        positions[nid] = (x, y)
    return LayoutResult(positions=positions)
