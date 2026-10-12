"""Tests for the graph bridge's agent-facing node/edge semantics."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from src.graph_bridge import GraphBridgeServer  # noqa: E402
from src.libs.graph_lib import EdgeItem, GraphWidget, NodeItem  # noqa: E402

_app = QApplication.instance() or QApplication([])


class GraphBridgeServerTest(unittest.TestCase):
    def setUp(self):
        self.gw = GraphWidget()
        self.server = GraphBridgeServer()
        self.server._graph_widget = self.gw
        self.server._node_item_cls = NodeItem

    def _nodes(self):
        return [i for i in self.gw._scene.items() if isinstance(i, NodeItem)]

    def _edges(self):
        return [i for i in self.gw._scene.items() if isinstance(i, EdgeItem)]

    def test_add_node_creates_and_places(self):
        res = self.server._add_node({"title": "example.com", "entity_type": "domain"})
        self.assertTrue(res["created"])
        self.assertEqual(res["entity_type"], "Domain")
        self.assertEqual(len(self._nodes()), 1)

    def test_add_node_rejects_unknown_type(self):
        res = self.server._add_node({"title": "x", "entity_type": "nanobot"})
        self.assertIn("error", res)
        self.assertIn("Person", res["valid_entity_types"])
        self.assertEqual(len(self._nodes()), 0)

    def test_add_node_requires_title(self):
        self.assertIn("error", self.server._add_node({"title": "  "}))

    def test_add_node_deduplicates_and_merges(self):
        first = self.server._add_node({"title": "alice", "entity_type": "Username"})
        second = self.server._add_node(
            {"title": "alice", "entity_type": "Username", "content": "found on X"}
        )
        self.assertFalse(second["created"])
        self.assertTrue(second["deduplicated"])
        self.assertEqual(first["node_id"], second["node_id"])
        self.assertEqual(len(self._nodes()), 1)
        self.assertIn("found on X", self._nodes()[0].content)

    def test_add_node_allow_duplicate(self):
        self.server._add_node({"title": "alice", "entity_type": "Username"})
        self.server._add_node(
            {
                "title": "alice",
                "entity_type": "Username",
                "allow_duplicate": True,
            }
        )
        self.assertEqual(len(self._nodes()), 2)

    def test_anchored_nodes_do_not_overlap(self):
        anchor = self.server._add_node({"title": "alice", "entity_type": "Username"})
        for i in range(6):
            self.server._add_node(
                {
                    "title": f"site{i}.com",
                    "entity_type": "Domain",
                    "anchor_id": anchor["node_id"],
                }
            )
        nodes = self._nodes()
        for i, a in enumerate(nodes):
            for b in nodes[i + 1 :]:
                separated = (
                    abs(a.pos().x() - b.pos().x()) >= a._width
                    or abs(a.pos().y() - b.pos().y()) >= a._height
                )
                self.assertTrue(separated)

    def test_add_edge_auto_ports_and_dedupe(self):
        a = self.server._add_node({"title": "a.com", "entity_type": "Domain"})
        b = self.server._add_node({"title": "b.com", "entity_type": "Domain"})
        res = self.server._add_edge(
            {
                "source_id": a["node_id"],
                "target_id": b["node_id"],
                "relationship": "owns",
            }
        )
        self.assertTrue(res["created"])
        self.assertIn(res["source_port"], {"left", "right", "top", "bottom"})
        dup = self.server._add_edge(
            {
                "source_id": b["node_id"],
                "target_id": a["node_id"],
                "relationship": "resolved_to",
            }
        )
        self.assertFalse(dup["created"])
        self.assertTrue(dup["duplicate"])
        self.assertEqual(len(self._edges()), 1)

    def test_add_edge_rejects_self_loop(self):
        a = self.server._add_node({"title": "a.com", "entity_type": "Domain"})
        res = self.server._add_edge(
            {"source_id": a["node_id"], "target_id": a["node_id"]}
        )
        self.assertIn("error", res)
        self.assertEqual(len(self._edges()), 0)

    def test_build_maps_refs(self):
        res = self.server._build(
            {
                "nodes": [
                    {"ref": "p", "title": "@alice", "entity_type": "Username"},
                    {
                        "ref": "e",
                        "title": "a@b.com",
                        "entity_type": "Email",
                        "anchor": "p",
                    },
                ],
                "edges": [
                    {"source": "p", "target": "e", "relationship": "registered_at"}
                ],
            }
        )
        self.assertEqual(len(res["node_ids"]), 2)
        self.assertEqual(len(res["nodes"]), 2)
        self.assertEqual(len(res["edges"]), 1)
        self.assertTrue(res["edges"][0]["created"])


if __name__ == "__main__":
    unittest.main()
