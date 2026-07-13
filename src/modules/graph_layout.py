from dataclasses import dataclass

import networkx as nx

LAYOUT_ALGORITHMS = {
    "spring": "Force-directed (Spring)",
    "kamada_kawai": "Kamada-Kawai",
    "shell": "Shell (Circular)",
    "spectral": "Spectral",
    "circular": "Circular",
}


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
