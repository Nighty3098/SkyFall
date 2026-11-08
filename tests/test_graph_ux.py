"""Tests for the graph canvas interaction layer (Maltego-style conveniences)."""

import asyncio
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QStatusBar  # noqa: E402

from src.controllers.graph_transform_controller import (  # noqa: E402
    ChildNodeDef,
    GraphTransformController,
    TransformDef,
    TransformResult,
)
from src.libs.graph_lib import EdgeItem, GraphWidget, NodeItem  # noqa: E402

_app = QApplication.instance() or QApplication([])


class GraphUxTest(unittest.TestCase):
    def setUp(self):
        self.gw = GraphWidget()
        self.gw._status_timer.stop()

    def _nodes(self):
        return [i for i in self.gw._scene.items() if isinstance(i, NodeItem)]

    def _edges(self):
        return [i for i in self.gw._scene.items() if isinstance(i, EdgeItem)]

    def _add(self, x, y, title="Node", etype="Person"):
        node = self.gw.add_node(QPointF(x, y), etype)
        node.title = title
        node.update()
        return node

    def _select(self, *nodes):
        self.gw._scene.clearSelection()
        for node in nodes:
            node.setSelected(True)

    def test_status_overlay_is_transient_and_layout_safe(self):
        window = self.gw.window()
        self.gw.status_message("Running transform")
        self.assertEqual(self.gw._status_text, "Running transform")
        self.assertTrue(self.gw._status_timer.isActive())
        self.assertIsNone(window.findChild(QStatusBar))
        self.assertIsNone(window.findChild(QLabel, "graphStatusLabel"))
        self.gw._clear_status()
        self.assertEqual(self.gw._status_text, "")
        self.assertFalse(self.gw._status_timer.isActive())

    def test_copy_paste_preserves_internal_edges(self):
        first = self._add(10, 20, "Alice")
        second = self._add(220, 20, "alice.dev", "Domain")
        self.gw.add_edge(first, second)
        self._select(first, second)

        self.assertTrue(self.gw.copy_selection())
        self.gw._undo_stack.clear()
        pasted = self.gw.paste_clipboard()

        self.assertEqual(len(pasted), 2)
        self.assertEqual(len(self._nodes()), 4)
        self.assertEqual(len(self._edges()), 2)
        self.assertNotEqual({n.id for n in pasted}, {first.id, second.id})
        self.assertEqual(len(self.gw._selected_nodes()), 2)

        self.assertTrue(self.gw.undo())
        self.assertEqual(len(self._nodes()), 2)
        self.assertEqual(len(self._edges()), 1)

    def test_duplicate_offsets_selection(self):
        node = self._add(40, 50, "Alice")
        self._select(node)
        duplicated = self.gw.duplicate_selection()

        self.assertEqual(len(duplicated), 1)
        self.assertEqual(len(self._nodes()), 2)
        self.assertEqual(duplicated[0].pos(), QPointF(80, 90))

    def test_cut_removes_selection_and_keeps_clipboard(self):
        node = self._add(40, 50, "Alice")
        self._select(node)
        self.assertTrue(self.gw.cut_selection())

        self.assertEqual(self._nodes(), [])
        self.assertIsNotNone(self.gw._clipboard)
        self.assertTrue(self.gw.paste_clipboard())
        self.assertEqual(len(self._nodes()), 1)

    def test_selection_tools_expand_and_match_entities(self):
        first = self._add(0, 0, "Alice", "Person")
        second = self._add(200, 0, "Bob", "Person")
        third = self._add(400, 0, "alice.dev", "Domain")
        self.gw.add_edge(first, second)
        self.gw.add_edge(second, third)
        self._select(first)

        self.assertEqual(self.gw.select_connected(), 2)
        self.assertEqual(len(self.gw._selected_nodes()), 2)

        self._select(first)
        self.assertEqual(self.gw.select_same_type(), 2)
        self.assertEqual({n.entity_type for n in self.gw._selected_nodes()}, {"Person"})

        self._select(first)
        self.assertEqual(self.gw.invert_selection(), 2)
        self.assertEqual(
            {n.id for n in self.gw._selected_nodes()}, {second.id, third.id}
        )

    def test_align_and_distribute(self):
        first = self._add(0, 0, "A")
        second = self._add(50, 50, "B")
        third = self._add(250, 100, "C")
        self._select(first, second, third)

        self.assertTrue(self.gw.align_selected("left"))
        self.assertEqual({n.pos().x() for n in self._nodes()}, {0.0})

        first.setPos(0, 0)
        second.setPos(50, 50)
        third.setPos(250, 100)
        self.assertTrue(self.gw.distribute_selected("horizontal"))
        centers = sorted(n.pos().x() + n._width / 2 for n in self._nodes())
        self.assertAlmostEqual(centers[1] - centers[0], centers[2] - centers[1])

    def test_connect_selected_sequence_and_all_pairs(self):
        first = self._add(0, 0, "A")
        second = self._add(200, 50, "B")
        third = self._add(400, 100, "C")
        self._select(first, second, third)

        self.assertEqual(self.gw.connect_selected("sequence"), 2)
        self.assertEqual(len(self._edges()), 2)
        self.assertEqual(self.gw.connect_selected("all"), 1)
        self.assertEqual(len(self._edges()), 3)
        self.assertEqual(self.gw.connect_selected("all"), 0)

    def test_fit_selection_frames_only_selected_nodes(self):
        self._add(0, 0, "A")
        second = self._add(1000, 1000, "B")
        self._select(second)
        before = self.gw.transform().m11()
        self.assertTrue(self.gw.fit_selection())
        self.assertNotEqual(self.gw.transform().m11(), before)
        view_center = self.gw.mapToScene(self.gw.viewport().rect().center())
        target = second.sceneBoundingRect().center()
        self.assertAlmostEqual(view_center.x(), target.x(), delta=1.0)
        self.assertAlmostEqual(view_center.y(), target.y(), delta=1.0)

    def test_minimap_can_be_toggled(self):
        self._add(0, 0, "Alice")
        self.assertTrue(self.gw._minimap_enabled)
        self.gw.set_minimap_visible(False)
        self.assertFalse(self.gw._minimap_enabled)
        self.gw.set_minimap_visible(True)
        self.assertTrue(self.gw._minimap_enabled)


class GraphTransformUxTest(unittest.TestCase):
    def setUp(self):
        self.gw = GraphWidget()
        self.gw._status_timer.stop()
        self.controller = GraphTransformController(self.gw, {}, plugin_dir=None)

    def _nodes(self):
        return [i for i in self.gw._scene.items() if isinstance(i, NodeItem)]

    def _edges(self):
        return [i for i in self.gw._scene.items() if isinstance(i, EdgeItem)]

    def _transform(self, name="Fake Transform"):
        async def handler(value, modules):
            del modules
            return TransformResult(
                children=[
                    ChildNodeDef(
                        title=f"{value} result",
                        entity_type="Domain",
                        content="result",
                    )
                ]
            )

        return TransformDef(
            name=name,
            description="Test transform",
            input_types=["Username"],
            output_type="Domain",
            relationship="resolved_to",
            handler=handler,
        )

    def _node(self, title="alice"):
        node = self.gw.add_node(QPointF(10, 20), "Username")
        node.title = title
        node.update()
        return node

    def test_async_transform_is_one_undo_step_and_selects_results(self):
        node = self._node()
        self.gw._undo_stack.clear()
        count = asyncio.run(self.controller._execute_async(node, self._transform()))

        self.assertEqual(count, 1)
        self.assertEqual(len(self.gw._undo_stack), 1)
        children = [n for n in self.gw._selected_nodes() if n.title == "alice result"]
        self.assertEqual(len(children), 1)
        self.assertEqual(len(self._nodes()), 2)
        self.assertEqual(len(self._edges()), 1)

        self.assertTrue(self.gw.undo())
        self.assertEqual(len(self._nodes()), 1)
        self.assertEqual(len(self._edges()), 0)

    def test_execute_many_groups_everything_into_one_undo_step(self):
        first = self._node("alice")
        second = self._node("bob")
        self.gw._undo_stack.clear()
        asyncio.run(
            self.controller._execute_many_async([first, second], self._transform())
        )

        self.assertEqual(len(self.gw._undo_stack), 1)
        titles = sorted(n.title for n in self._nodes())
        self.assertEqual(titles, ["alice", "alice result", "bob", "bob result"])
        self.assertEqual(
            {n.title for n in self.gw._selected_nodes()},
            {"alice result", "bob result"},
        )

        self.assertTrue(self.gw.undo())
        self.assertEqual(len(self._nodes()), 2)
        self.assertEqual(len(self._edges()), 0)
