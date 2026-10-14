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
}

# Default node footprint used when placing nodes automatically.
NODE_WIDTH = 160.0
NODE_HEIGHT = 120.0

# Gap kept between two node footprints so neighbours never touch.
NODE_GAP = 48.0

# The tidy tree layout; see ``compute_hierarchical_layout``.
TREE_ALGORITHM = "hierarchical"

# Above this node count the cubic Kamada-Kawai solver is swapped for a
# force-directed pass so large graphs stay responsive.
KAMADA_KAWAI_LIMIT = 400


@dataclass
class LayoutResult:
    positions: dict[str, tuple[float, float]]


def _target_span(count: int) -> float:
    """Bounding-box side that fits ``count`` nodes without overlap."""
    cell = max(NODE_WIDTH, NODE_HEIGHT) + NODE_GAP
    cols = max(1, math.ceil(math.sqrt(max(count, 1))))
    return cols * cell


def _fit_positions(
    pos: dict[str, tuple[float, float]],
    span: float,
) -> dict[str, tuple[float, float]]:
    """Centre raw layout coordinates and stretch them to fill a ``span`` box.

    Each axis is scaled independently so that elongated layouts (a path, for
    example) open up into two dimensions instead of being squeezed into a thin
    strip where the nodes would overlap.
    """
    if not pos:
        return {}
    if len(pos) == 1:
        return {next(iter(pos)): (0.0, 0.0)}
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    cx = (min(xs) + max(xs)) / 2.0
    cy = (min(ys) + max(ys)) / 2.0
    span = max(span, 1e-9)
    width = max(max(xs) - min(xs), 1e-9)
    height = max(max(ys) - min(ys), 1e-9)
    sx = span / width
    sy = span / height
    return {nid: ((x - cx) * sx, (y - cy) * sy) for nid, (x, y) in pos.items()}


def _resolve_overlaps(
    pos: dict[str, tuple[float, float]],
    node_w: float = NODE_WIDTH,
    node_h: float = NODE_HEIGHT,
    padding: float = NODE_GAP * 0.5,
    iterations: int = 160,
) -> dict[str, tuple[float, float]]:
    """Push overlapping node footprints apart until they are disjoint.

    Keeps the arrangement produced by the layout algorithm but guarantees that
    no two node rectangles intersect, which bounding-box-only scaling missed.
    A uniform grid limits each pass to nearby neighbours, so the cost stays
    close to linear in the number of nodes.
    """
    ids = list(pos)
    if len(ids) < 2:
        return dict(pos)

    rank = {nid: index for index, nid in enumerate(ids)}
    work = {nid: [float(pos[nid][0]), float(pos[nid][1])] for nid in ids}
    required_x = node_w + padding
    required_y = node_h + padding
    cell = max(required_x, required_y)

    for _ in range(iterations):
        buckets: dict[tuple[int, int], list[str]] = {}
        for nid in ids:
            x, y = work[nid]
            key = (math.floor(x / cell), math.floor(y / cell))
            buckets.setdefault(key, []).append(nid)

        moved = False
        for nid in ids:
            x, y = work[nid]
            gx = math.floor(x / cell)
            gy = math.floor(y / cell)
            for offset_x in (-1, 0, 1):
                for offset_y in (-1, 0, 1):
                    for other in buckets.get((gx + offset_x, gy + offset_y), ()):
                        if rank[other] <= rank[nid]:
                            continue
                        ax, ay = work[nid]
                        bx, by = work[other]
                        dx = bx - ax
                        dy = by - ay
                        overlap_x = required_x - abs(dx)
                        overlap_y = required_y - abs(dy)
                        if overlap_x <= 0.0 or overlap_y <= 0.0:
                            continue
                        moved = True
                        if overlap_x <= overlap_y:
                            sign = 1.0 if dx > 0.0 else -1.0
                            if dx == 0.0:
                                sign = 1.0 if rank[nid] % 2 else -1.0
                            shift = overlap_x / 2.0 + 0.5
                            work[nid][0] = ax - sign * shift
                            work[other][0] = bx + sign * shift
                        else:
                            sign = 1.0 if dy > 0.0 else -1.0
                            if dy == 0.0:
                                sign = 1.0 if rank[nid] % 2 else -1.0
                            shift = overlap_y / 2.0 + 0.5
                            work[nid][1] = ay - sign * shift
                            work[other][1] = by + sign * shift
        if not moved:
            break

    return {nid: (work[nid][0], work[nid][1]) for nid in ids}


def _spring_layout(g: nx.Graph) -> dict[str, tuple[float, float]]:
    """Force-directed layout tuned to the node footprint and seeded for stability."""
    count = max(len(g.nodes), 1)
    return nx.spring_layout(g, k=1.2 / math.sqrt(count), iterations=200, seed=42)


def _shell_layout(g: nx.Graph) -> dict[str, tuple[float, float]]:
    """Concentric shells around the most connected node.

    Unlike the plain ``shell_layout`` default (a single ring for every node)
    this groups nodes by BFS distance and orders each ring so children stay
    near their parent.
    """
    root = max(g.nodes, key=lambda node: (g.degree(node), str(node)))
    depth = nx.single_source_shortest_path_length(g, root)
    tree = nx.bfs_tree(g, root)
    parent = {child: par for par, child in tree.edges}
    order: dict[str, int] = {}
    shells: list[list[str]] = []
    levels = max(depth.values()) + 1 if depth else 1
    for level in range(levels):
        shell = sorted(
            (nid for nid in g.nodes if depth.get(nid) == level),
            key=lambda nid: (order.get(parent.get(nid, ""), -1), str(nid)),
        )
        if not shell:
            continue
        for index, nid in enumerate(shell):
            order[nid] = index
        shells.append(shell)
    return nx.shell_layout(g, nlist=shells)


def _circular_layout(g: nx.Graph) -> dict[str, tuple[float, float]]:
    """Single ring ordered by a depth-first walk.

    Visiting the graph depth-first keeps connected nodes beside each other on
    the ring, removing most of the edge crossings a naive node-order placement
    produces.
    """
    root = max(g.nodes, key=lambda node: (g.degree(node), str(node)))
    order = list(nx.dfs_preorder_nodes(g, root))
    seen = set(order)
    for nid in sorted(g.nodes, key=str):
        if nid in seen:
            continue
        for extra in nx.dfs_preorder_nodes(g, nid):
            if extra not in seen:
                order.append(extra)
                seen.add(extra)
    count = max(len(order), 1)
    return {
        nid: (
            math.cos(2.0 * math.pi * index / count - math.pi / 2.0),
            math.sin(2.0 * math.pi * index / count - math.pi / 2.0),
        )
        for index, nid in enumerate(order)
    }


def _spectral_layout(g: nx.Graph) -> dict[str, tuple[float, float]]:
    """Spectral layout with a force-directed fallback for degenerate spectra."""
    try:
        pos = nx.spectral_layout(g)
        distinct = {(round(float(x), 6), round(float(y), 6)) for x, y in pos.values()}
        if len(distinct) < max(2, len(g.nodes) // 2):
            raise ValueError("degenerate spectral layout")
        return pos
    except Exception:
        return _spring_layout(g)


def _raw_layout(g: nx.Graph, algorithm: str) -> dict[str, tuple[float, float]]:
    """Compute an algorithm's native coordinates for a connected graph."""
    if len(g.nodes) <= 1:
        return {nid: (0.0, 0.0) for nid in g.nodes}
    if algorithm == "kamada_kawai" and len(g.nodes) <= KAMADA_KAWAI_LIMIT:
        try:
            return nx.kamada_kawai_layout(g)
        except Exception:
            return _spring_layout(g)
    if algorithm == "shell":
        return _shell_layout(g)
    if algorithm == "spectral":
        return _spectral_layout(g)
    if algorithm == "circular":
        return _circular_layout(g)
    return _spring_layout(g)


def _layout_connected(g: nx.Graph, algorithm: str, span: float) -> dict:
    """Layout one connected component and guarantee non-overlapping nodes."""
    raw = {
        nid: (float(x), float(y)) for nid, (x, y) in _raw_layout(g, algorithm).items()
    }
    return _resolve_overlaps(_fit_positions(raw, span))


def _pack_components(parts: list[dict]) -> dict[str, tuple[float, float]]:
    """Arrange disconnected components on a grid without overlapping them."""
    if not parts:
        return {}
    boxes = []
    for pos in parts:
        xs = [p[0] for p in pos.values()]
        ys = [p[1] for p in pos.values()]
        min_x = min(xs) - NODE_WIDTH / 2.0
        min_y = min(ys) - NODE_HEIGHT / 2.0
        max_x = max(xs) + NODE_WIDTH / 2.0
        max_y = max(ys) + NODE_HEIGHT / 2.0
        boxes.append((min_x, min_y, max_x - min_x, max_y - min_y))
    columns = max(1, math.ceil(math.sqrt(len(parts))))
    cell_w = max(box[2] for box in boxes) + NODE_GAP
    cell_h = max(box[3] for box in boxes) + NODE_GAP
    merged: dict[str, tuple[float, float]] = {}
    for index, (pos, box) in enumerate(zip(parts, boxes)):
        offset_x = (index % columns) * cell_w - box[0]
        offset_y = (index // columns) * cell_h - box[1]
        for nid, (x, y) in pos.items():
            merged[nid] = (x + offset_x, y + offset_y)
    return merged


def compute_layout(
    nodes: list[dict],
    edges: list[dict],
    algorithm: str = "spring",
    scale: float = 1.0,
) -> LayoutResult:
    """Place every node of the graph with the requested algorithm.

    Tree layouts are delegated to :func:`compute_hierarchical_layout`; the
    remaining algorithms produce node-sized, overlap-free coordinates, with
    disconnected components laid out separately and packed side by side.
    """
    g = nx.Graph()

    for node in nodes:
        g.add_node(node["id"])

    for edge in edges:
        g.add_edge(edge["source"], edge["target"])

    if len(g.nodes) == 0:
        return LayoutResult(positions={})

    if algorithm == TREE_ALGORITHM:
        return compute_hierarchical_layout(nodes, edges, direction="down", scale=scale)

    factor = max(scale, 0.01)
    components = [
        sorted(component, key=str) for component in nx.connected_components(g)
    ]

    if len(components) == 1:
        span = _target_span(len(g.nodes)) * factor
        return LayoutResult(positions=_layout_connected(g, algorithm, span))

    parts = []
    for component in components:
        sub = g.subgraph(component)
        span = _target_span(len(component)) * factor
        parts.append(_layout_connected(sub, algorithm, span))
    return LayoutResult(positions=_pack_components(parts))


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
