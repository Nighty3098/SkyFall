"""Tests for graph canvas undo/redo."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from src.libs.graph_lib import EdgeItem, GraphWidget, NodeItem  # noqa: E402

_app = QApplication.instance() or QApplication([])


class GraphUndoTest(unittest.TestCase):
    def setUp(self):
        self.gw = GraphWidget()

    def _nodes(self):
        return [i for i in self.gw._scene.items() if isinstance(i, NodeItem)]

    def _edges(self):
        return [i for i in self.gw._scene.items() if isinstance(i, EdgeItem)]

    def _find(self, node_id):
        return next((n for n in self._nodes() if n.id == node_id), None)

    def test_undo_empty_stack_is_noop(self):
        self.assertFalse(self.gw.undo())
        self.assertFalse(self.gw.redo())

    def test_add_node_undo_redo(self):
        node = self.gw.add_node(QPointF(10, 20))
        self.assertEqual(len(self._nodes()), 1)
        self.assertTrue(self.gw.undo())
        self.assertEqual(len(self._nodes()), 0)
        self.assertTrue(self.gw.redo())
        self.assertEqual(len(self._nodes()), 1)
        self.assertIsNotNone(self._find(node.id))

    def test_remove_node_restores_edges(self):
        a = self.gw.add_node(QPointF(0, 0))
        b = self.gw.add_node(QPointF(300, 0))
        self.gw.add_edge(a, b)
        a_id = a.id
        self.gw.remove_node(a)
        self.assertEqual(len(self._nodes()), 1)
        self.assertEqual(len(self._edges()), 0)
        self.assertTrue(self.gw.undo())
        self.assertEqual(len(self._nodes()), 2)
        self.assertEqual(len(self._edges()), 1)
        self.assertIsNotNone(self._find(a_id))

    def test_remove_edge_undo(self):
        a = self.gw.add_node(QPointF(0, 0))
        b = self.gw.add_node(QPointF(300, 0))
        self.gw.add_edge(a, b)
        self.gw.remove_edge(self._edges()[0])
        self.assertEqual(len(self._edges()), 0)
        self.assertTrue(self.gw.undo())
        self.assertEqual(len(self._edges()), 1)

    def test_clear_graph_undo(self):
        a = self.gw.add_node(QPointF(0, 0))
        b = self.gw.add_node(QPointF(300, 0))
        self.gw.add_edge(a, b)
        self.gw.clear_graph()
        self.assertEqual(len(self._nodes()), 0)
        self.assertTrue(self.gw.undo())
        self.assertEqual(len(self._nodes()), 2)
        self.assertEqual(len(self._edges()), 1)

    def test_new_action_clears_redo(self):
        a = self.gw.add_node(QPointF(0, 0))
        a_id = a.id
        self.gw.undo()
        self.gw.add_node(QPointF(1, 1))
        self.assertFalse(self.gw.redo())
        self.assertIsNone(self._find(a_id))

    def test_bulk_edit_is_single_step(self):
        self.gw.begin_bulk_edit()
        self.gw.add_node(QPointF(0, 0))
        self.gw.add_node(QPointF(10, 10))
        self.gw.add_node(QPointF(20, 20))
        self.gw.end_bulk_edit()
        self.assertEqual(len(self._nodes()), 3)
        self.assertTrue(self.gw.undo())
        self.assertEqual(len(self._nodes()), 0)

    def test_move_undo_restores_position(self):
        node = self.gw.add_node(QPointF(0, 0))
        node_id = node.id
        before = QPointF(node.pos())
        self.gw._move_before_positions = {node: before}
        node.setPos(QPointF(120, 80))
        self.gw._finish_move_tracking()
        self.assertTrue(self.gw.undo())
        restored = self._find(node_id)
        self.assertIsNotNone(restored)
        self.assertEqual(restored.pos(), before)

    def test_click_without_move_adds_no_undo_step(self):
        node = self.gw.add_node(QPointF(5, 5))
        self.gw._move_before_positions = {node: node.pos()}
        self.gw._finish_move_tracking()
        # Only the add snapshot remains; one undo clears the graph.
        self.assertTrue(self.gw.undo())
        self.assertEqual(len(self._nodes()), 0)

    def test_snapshot_is_isolated_from_later_edits(self):
        node = self.gw.add_node(QPointF(0, 0))
        node_id = node.id
        node.evidence = ["original"]
        self.gw.remove_node(node)
        # Mutating a live node after the snapshot must not corrupt history.
        self.gw.undo()
        restored = self._find(node_id)
        self.assertEqual(restored.evidence, ["original"])

    def test_undo_limit_trims_history(self):
        self.gw._undo_limit = 3
        for i in range(6):
            self.gw.add_node(QPointF(i, i))
        self.assertEqual(len(self.gw._undo_stack), 3)


if __name__ == "__main__":
    unittest.main()
