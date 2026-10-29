import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication

from src.controllers import graph_layout_controller as layout_module
from src.controllers.graph_layout_controller import GraphLayoutController
from src.libs.graph_lib import GraphWidget
from src.modules.graph_layout import LAYOUT_ALGORITHMS, compute_layout


def _app():
    return QApplication.instance() or QApplication([])


def test_layout_menu_action_applies_to_selected_nodes_only(monkeypatch):
    _app()
    graph = GraphWidget()
    first = graph._add_node_now(QPointF(0, 0))
    second = graph._add_node_now(QPointF(400, 0))
    third = graph._add_node_now(QPointF(900, 0))
    graph._add_edge_now(first, second)
    graph._add_edge_now(second, third)
    first.setSelected(True)
    second.setSelected(True)
    unchanged_position = third.pos()
    calls = []

    def fake_layout(nodes, edges, algorithm):
        calls.append((nodes, edges, algorithm))
        return SimpleNamespace(
            positions={nodes[0]["id"]: (0, 0), nodes[1]["id"]: (300, 0)}
        )

    monkeypatch.setattr(layout_module, "compute_layout", fake_layout)
    monkeypatch.setattr(graph, "fit_to_view", lambda: None)
    controller = GraphLayoutController(None, graph)

    controller.apply_layout("circular")

    nodes, edges, algorithm = calls[0]
    assert {node["id"] for node in nodes} == {first.id, second.id}
    assert len(edges) == 1
    assert (edges[0]["source"], edges[0]["target"]) == (first.id, second.id)
    assert algorithm == "circular"
    assert first.pos() != QPointF(0, 0)
    assert second.pos() != QPointF(400, 0)
    assert third.pos() == unchanged_position


def test_layout_without_selection_applies_to_entire_graph(monkeypatch):
    _app()
    graph = GraphWidget()
    first = graph._add_node_now(QPointF(0, 0))
    second = graph._add_node_now(QPointF(400, 0))
    calls = []

    def fake_layout(nodes, edges, algorithm):
        calls.append(nodes)
        return SimpleNamespace(positions={node["id"]: (0, 0) for node in nodes})

    monkeypatch.setattr(layout_module, "compute_layout", fake_layout)
    monkeypatch.setattr(graph, "fit_to_view", lambda: None)
    controller = GraphLayoutController(None, graph)

    controller.apply_layout("spring")

    assert {node["id"] for node in calls[0]} == {first.id, second.id}


def test_telegram_layout_is_available_and_clusters_telegram_entities():
    nodes = [
        {"id": "channel:news", "entity_type": "Organization"},
        {"id": "user:alice", "entity_type": "Person"},
        {"id": "user:bob", "entity_type": "Person"},
        {"id": "user:carol", "entity_type": "Person"},
        {"id": "domain:example.org", "entity_type": "Domain"},
    ]
    edges = [
        {
            "source": "channel:news",
            "target": "user:alice",
            "label": "member · posted x3",
        },
        {"source": "user:alice", "target": "user:bob", "label": "replier x2"},
        {"source": "user:bob", "target": "user:carol", "label": "forwarded"},
        {
            "source": "user:alice",
            "target": "domain:example.org",
            "label": "mentions",
        },
    ]

    result = compute_layout(nodes, edges, algorithm="telegram")

    assert LAYOUT_ALGORITHMS["telegram"] == "Telegram Hub-and-Cluster"
    assert set(result.positions) == {node["id"] for node in nodes}
    channel_x, channel_y = result.positions["channel:news"]
    alice_x, alice_y = result.positions["user:alice"]
    carol_x, carol_y = result.positions["user:carol"]
    assert (alice_x - channel_x) ** 2 + (alice_y - channel_y) ** 2 < 500**2
    assert (carol_x - channel_x) ** 2 + (carol_y - channel_y) ** 2 < 500**2
    assert (
        result.positions == compute_layout(nodes, edges, algorithm="telegram").positions
    )
