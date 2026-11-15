"""Integration tests for graph-widget entity resolution and undo."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from src.libs.graph_lib import EdgeItem, GraphWidget, NodeItem  # noqa: E402

_app = QApplication.instance() or QApplication([])


def _node(node_id, title, entity_type="Person", content="", evidence=None, **extra):
    node = {
        "id": node_id,
        "title": title,
        "entity_type": entity_type,
        "content": content,
        "evidence": list(evidence or []),
    }
    node.update(extra)
    return node


class GraphEntityResolutionTest(unittest.TestCase):
    def setUp(self):
        self.gw = GraphWidget()
        self.changed = []
        self.gw.graphChanged.connect(self.changed.append)

    def tearDown(self):
        self.gw.deleteLater()

    def _load(self, nodes, edges=None):
        self.gw.from_dict({"nodes": nodes, "edges": list(edges or [])})
        self.changed.clear()

    def _nodes(self):
        return [item for item in self.gw._scene.items() if isinstance(item, NodeItem)]

    def _edges(self):
        return [item for item in self.gw._scene.items() if isinstance(item, EdgeItem)]

    def _titles(self):
        return sorted(node.title for node in self._nodes())

    def test_auto_merge_collapses_duplicate_person(self):
        self._load(
            [
                _node(
                    "a", "Alice", content="Email: alice@example.com", evidence=["one"]
                ),
                _node(
                    "b", "alice", content="Email: ALICE@example.com", evidence=["two"]
                ),
                _node("c", "Bob", content="Email: bob@example.com"),
            ]
        )
        reports = self.gw.auto_merge_exact_duplicates(notify=False)

        self.assertEqual(len(reports), 1)
        self.assertEqual(len(self._nodes()), 2)
        survivor = next(node for node in self._nodes() if node.title.lower() == "alice")
        self.assertEqual(set(survivor.evidence), {"one", "two"})
        self.assertIn("Alice", survivor.aliases)
        self.assertIn("alice", survivor.aliases)
        self.assertEqual(len(survivor.merged_from), 1)
        self.assertEqual(survivor.merged_from[0]["id"], reports[0]["removed_ids"][0])
        self.assertTrue(survivor.metadata.get("resolution"))
        self.assertEqual(self.changed[-1], "entities_merged")

    def test_merge_rewires_and_deduplicates_edges(self):
        self._load(
            [
                _node("a", "Alice", evidence=["one", "two"]),
                _node("b", "Alice", evidence=["three"]),
                _node("c", "Bob"),
            ],
            [
                {
                    "source": "a",
                    "target": "c",
                    "relationship_type": "knows",
                    "label": "friend",
                },
                {
                    "source": "b",
                    "target": "c",
                    "relationship_type": "knows",
                    "label": "colleague",
                },
            ],
        )
        self.gw.auto_merge_exact_duplicates(notify=False)

        self.assertEqual(len(self._nodes()), 2)
        self.assertEqual(len(self._edges()), 1)
        edge = self._edges()[0]
        bob = next(node for node in self._nodes() if node.title == "Bob")
        self.assertIn(bob, (edge.source, edge.target))
        self.assertIn("friend", edge.label)
        self.assertIn("colleague", edge.label)

    def test_edge_between_duplicates_becomes_self_loop_and_is_dropped(self):
        self._load(
            [_node("a", "Alice"), _node("b", "alice")],
            [{"source": "a", "target": "b", "relationship_type": "aliases"}],
        )
        self.gw.auto_merge_exact_duplicates(notify=False)
        self.assertEqual(len(self._nodes()), 1)
        self.assertEqual(self._edges(), [])

    def test_undo_restores_merged_nodes_and_edges(self):
        self._load(
            [
                _node("a", "Alice", evidence=["one"]),
                _node("b", "Alice", evidence=["two"]),
                _node("c", "Bob"),
            ],
            [
                {"source": "a", "target": "c", "relationship_type": "knows"},
                {"source": "b", "target": "c", "relationship_type": "knows"},
            ],
        )
        self.gw.auto_merge_exact_duplicates(notify=False)
        self.assertEqual(len(self._nodes()), 2)

        self.assertTrue(self.gw.undo())
        self.assertEqual(len(self._nodes()), 3)
        self.assertEqual(len(self._edges()), 2)
        self.assertEqual(self._titles(), ["Alice", "Alice", "Bob"])

        self.assertTrue(self.gw.redo())
        self.assertEqual(len(self._nodes()), 2)
        self.assertEqual(len(self._edges()), 1)

    def test_auto_merge_respects_disabled_setting(self):
        self.gw.set_auto_resolve_enabled(False)
        self._load([_node("a", "Alice"), _node("b", "alice")])
        self.assertEqual(self.gw.auto_merge_exact_duplicates(notify=False), [])
        self.assertEqual(len(self._nodes()), 2)

    def test_review_duplicates_are_not_merged_automatically(self):
        self._load(
            [
                _node("a", "J. Smith", content=""),
                _node("b", "John Smith", content=""),
            ]
        )
        groups = self.gw.find_entity_duplicates(include_review=True)
        self.assertEqual(len(groups), 1)
        self.assertFalse(groups[0].auto)

        self.assertEqual(self.gw.auto_merge_exact_duplicates(notify=False), [])
        self.assertEqual(len(self._nodes()), 2)
        self.assertEqual(self.changed, [])

    def test_duplicate_discovery_can_be_limited_to_selection(self):
        self._load(
            [
                _node("a", "Alice"),
                _node("b", "alice"),
                _node("c", "Carol"),
                _node("d", "carol"),
            ]
        )
        for node in self._nodes():
            node.setSelected(node.id in {"a", "b"})
        groups = self.gw.find_entity_duplicates(include_review=True, selected_only=True)
        self.assertEqual(len(groups), 1)
        self.assertEqual(set(groups[0].node_ids), {"a", "b"})

    def test_manual_merge_of_unrelated_selected_nodes(self):
        self._load([_node("a", "one"), _node("b", "two")])
        for node in self._nodes():
            node.setSelected(True)
        reports = self.gw.merge_selected_entities()

        self.assertEqual(len(reports), 1)
        self.assertEqual(len(self._nodes()), 1)
        survivor = self._nodes()[0]
        self.assertEqual(set(survivor.aliases), {"one", "two"})
        self.assertEqual(reports[0]["reasons"], ["manual selection"])
        self.assertEqual(self.changed[-1], "entities_merged")

    def test_merge_without_duplicates_is_noop(self):
        self._load([_node("a", "Alice"), _node("b", "Bob")])
        self.assertEqual(self.gw.auto_merge_exact_duplicates(notify=False), [])
        self.assertEqual(self.changed, [])
        self.assertEqual(len(self._nodes()), 2)


if __name__ == "__main__":
    unittest.main()
